from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, model_validator

class AgentStep(BaseModel):
    thought: str = Field(
        description="Explain your reasoning, what you have learned so far, and why you are taking the next action."
    )
    action: Optional[str] = Field(
        default=None,
        description="The name of the tool you want to call. Must be one of the available tools. Leave empty if you are ready to provide a final response."
    )
    action_input: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The dictionary of arguments to pass to the tool. Leave empty if you are not calling a tool."
    )
    final_response: Optional[str] = Field(
        default=None,
        description="The final answer to the user. Only populate this when you are completely done and have all the information you need."
    )

    @model_validator(mode="after")
    def validate_action_or_response(self) -> "AgentStep":
        if not self.action and not self.final_response:
            raise ValueError("Either 'action' or 'final_response' must be populated.")
        if self.action and self.final_response:
            raise ValueError("Cannot provide both 'action' and 'final_response' in a single step.")
        if self.action and self.action_input is None:
            raise ValueError("Tool 'action' was specified but 'action_input' is missing.")
        return self


class SessionState(BaseModel):
    user_name: Optional[str] = None
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    summary_of_past_conversations: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
