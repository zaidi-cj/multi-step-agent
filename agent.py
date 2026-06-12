import time
import json
import google.generativeai as genai
from typing import List, Dict, Any, Optional
from schemas import AgentStep, SessionState
from tools import get_tool_definitions_string, execute_tool
from config import GEMINI_API_KEY

class Agent:
    def __init__(self, session: SessionState, max_steps: int = 8, max_retries: int = 3):
        self.session = session
        self.max_steps = max_steps
        self.max_retries = max_retries
        
        # Configure Gemini API client
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Initialize the model with system instruction and JSON output mode
        self.model = genai.GenerativeModel(
            model_name="models/gemini-3.5-flash",
            system_instruction=self._get_system_instruction(),
            generation_config={
                "response_mime_type": "application/json"
            }
        )

    def _get_system_instruction(self) -> str:
        tools_str = get_tool_definitions_string()
        user_name_str = f"The user's name is: {self.session.user_name}." if self.session.user_name else "The user's name is not known yet."
        
        return f"""You are a highly structured multi-step AI reasoning agent.
You solve tasks step-by-step by generating thoughts, choosing actions (calling tools), and reflecting on observations.

{user_name_str}

You MUST format your output strictly as a JSON object adhering to this schema:
{{
  "thought": "Reasoning about the current state, what was learned from past tools, and what to do next.",
  "action": "Name of the tool to run, or null if ready to give the final response.",
  "action_input": {{ "arg_1": "value_1", ... }} or null,
  "final_response": "The final answer to the user, or null if calling a tool."
}}

Available Tools:
{tools_str}

Core Instructions:
1. Every response must contain a detailed 'thought'. Explain what you are doing.
2. If you need information you don't have, or need to calculate or write a note, call the appropriate tool. Set 'action' to the tool name and populate 'action_input' with arguments. Keep 'final_response' as null.
3. Once you have solved the request or have all required information, provide your final response in 'final_response', and set 'action' and 'action_input' to null.
4. If a tool fails (e.g. returns an error message), don't give up. In your next step's 'thought', analyze the error and try to fix the arguments or try a different approach.
5. If the user mentions their name or preferences, remember to refer to them appropriately.
"""

    def _generate_content_with_retry(self, messages: List[Dict[str, Any]], model_override: Optional[genai.GenerativeModel] = None) -> str:
        """Queries Gemini, catching rate limit exceptions (429) and retrying with exponential backoff."""
        model = model_override or self.model
        api_retries = 3
        delay = 8  # Start with an 8-second sleep to clear most 5-RPM limit blocks
        
        for attempt in range(api_retries):
            try:
                response = model.generate_content(messages)
                return response.text
            except Exception as e:
                err_msg = str(e)
                # Check for 429 rate limit or quota exceeded exceptions
                if "429" in err_msg or "ResourceExhausted" in err_msg or "quota" in err_msg.lower():
                    if attempt < api_retries - 1:
                        print(f"\n\033[93m[Rate Limit Recovery] Quota Exceeded (429). Retrying in {delay} seconds...\033[0m")
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff
                        continue
                raise e
        return ""

    def run(self, user_prompt: str) -> str:
        """Runs the multi-step reasoning agent loop for a given prompt."""
        messages: List[Dict[str, Any]] = []

        # 1. Inject persistent session memory context if available
        if self.session.summary_of_past_conversations:
            messages.append({
                "role": "user",
                "parts": [f"[System Memory of Past Sessions:\n{self.session.summary_of_past_conversations}]"]
            })
            messages.append({
                "role": "model",
                "parts": [json.dumps({
                    "thought": "I have loaded the summary of past conversations. I will use this context to help the user.",
                    "action": None,
                    "action_input": None,
                    "final_response": "Understood. I have retrieved our history and am ready to assist you!"
                })]
            })

        # Append previous conversation history from the current active session
        for msg in self.session.conversation_history:
            messages.append(msg)

        # Append the new user input
        messages.append({"role": "user", "parts": [user_prompt]})

        step_num = 0
        retry_count = 0

        while step_num < self.max_steps:
            try:
                # Query Gemini with built-in API retry logic
                response_text = self._generate_content_with_retry(messages)
            except Exception as e:
                return f"Error connecting to Gemini API: {str(e)}"

            # 2. Structured Output Parsing & Failure Recovery (JSON / Schema validation)
            try:
                parsed_step = AgentStep.model_validate_json(response_text)
                
                # Successful parse - reset step retry counter
                retry_count = 0
            except Exception as e:
                retry_count += 1
                if retry_count > self.max_retries:
                    return f"Failure Recovery Error: Failed to parse output after {self.max_retries} retries. Last error: {str(e)}"
                
                print(f"\n[Parser Recovery] Warning: Failed to parse model output (Attempt {retry_count}/{self.max_retries}). Feedback loop triggered.")
                
                # We feed the malformed response and the parsing error back to the model
                messages.append({"role": "model", "parts": [response_text]})
                messages.append({
                    "role": "user",
                    "parts": [f"Parser Error: Your output did not match the JSON schema. Error: {str(e)}. Please correct your syntax and return a valid JSON object matching the schema."]
                })
                continue

            # Display reasoning step
            print(f"\n\033[94m--- [Agent Step {step_num + 1}] ---\033[0m")
            print(f"\033[93mThought:\033[0m {parsed_step.thought}")

            # Append the valid assistant response to the message log
            messages.append({"role": "model", "parts": [response_text]})

            # 3. Action Execution / Tool Call vs. Final Answer
            if parsed_step.final_response:
                print(f"\033[92mFinal Response:\033[0m {parsed_step.final_response}")
                # Save the active message logs back to the session state
                self.session.conversation_history = messages
                return parsed_step.final_response

            if parsed_step.action:
                print(f"\033[96mAction:\033[0m {parsed_step.action}")
                print(f"\033[96mArguments:\033[0m {parsed_step.action_input}")

                # Execute the tool and capture any execution exceptions
                try:
                    observation = execute_tool(parsed_step.action, parsed_step.action_input or {})
                except Exception as e:
                    observation = f"Error: Tool execution raised exception: {str(e)}"

                print(f"\033[95mObservation:\033[0m {observation}")

                # Feed the observation back to the model as a user message
                messages.append({
                    "role": "user",
                    "parts": [f"Observation: {observation}"]
                })

                step_num += 1

        return "Error: Agent reached maximum steps without providing a final response."

    def summarize_session(self) -> str:
        """Summarizes the current conversation history to compress persistent memory."""
        if not self.session.conversation_history:
            return ""

        summary_prompt = "Summarize the key details (e.g. user's name, preferences, findings, or notes created) from this conversation in 3-4 bullet points. Do not include raw tool calls, only high-level outcomes:\n\nTranscript:\n"
        for msg in self.session.conversation_history:
            role = msg["role"]
            content = msg["parts"][0]
            summary_prompt += f"{role.upper()}: {content}\n"

        try:
            model = genai.GenerativeModel("models/gemini-3.5-flash")
            response_text = self._generate_content_with_retry(summary_prompt, model_override=model)
            return response_text.strip()
        except Exception as e:
            return f"Summary failed: {str(e)}"
