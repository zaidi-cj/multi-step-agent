import os
import sys
from memory import load_session, save_session
from agent import Agent

def print_help():
    print("\nCommands:")
    print("  exit   - Save session, summarize history, and exit.")
    print("  clear  - Clear active conversation history (keeps long-term memory summary).")
    print("  status - Show the current persistent session state (JSON memory contents).")
    print("  help   - Print this help message.")

def main():
    print("==========================================================")
    print("       🚀 Multi-Step AI Agent with Persistent Memory      ")
    print("==========================================================")
    
    # Initialize ANSI escape sequences in Windows PowerShell/Command Prompt
    os.system('')

    # Load session state
    session = load_session()

    if session.user_name:
        print(f"\nWelcome back, \033[92m{session.user_name}\033[0m!")
    else:
        print("\nWelcome! What is your name?")
        name = input("Your Name: ").strip()
        if name:
            session.user_name = name
            save_session(session)
            print(f"Nice to meet you, \033[92m{session.user_name}\033[0m!")

    if session.summary_of_past_conversations:
        print("\n\033[94m[Memory Retrieved]\033[0m Past Context Summary:")
        print(session.summary_of_past_conversations)

    print_help()

    while True:
        try:
            user_input = input("\n\033[92mUser:\033[0m ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

        if not user_input:
            continue

        if user_input.lower() == "exit":
            print("\nSummarizing conversation and saving session context...")
            agent = Agent(session)
            if session.conversation_history:
                summary = agent.summarize_session()
                if summary and not summary.startswith("Summary failed"):
                    # Append new summaries with a clean separator
                    if session.summary_of_past_conversations:
                        session.summary_of_past_conversations += f"\n- {summary}"
                    else:
                        session.summary_of_past_conversations = f"- {summary}"
            
            # Reset active conversation history since it is summarized
            session.conversation_history = []
            save_session(session)
            print("Session saved successfully. Goodbye!")
            break

        elif user_input.lower() == "clear":
            session.conversation_history = []
            save_session(session)
            print("Active conversation history cleared.")
            continue

        elif user_input.lower() == "status":
            print("\n--- Current Session State (memory.json) ---")
            print(f"User Name: {session.user_name}")
            print(f"User Preferences: {session.user_preferences}")
            print(f"Summary of Past Conversations:\n{session.summary_of_past_conversations}")
            print(f"Active History Size: {len(session.conversation_history)} messages")
            continue

        elif user_input.lower() == "help":
            print_help()
            continue

        # Run the agent reasoning loop
        print("\nRunning agent reasoning loop...")
        agent = Agent(session)
        result = agent.run(user_input)
        
        # If the result represents an error message, print it to the user
        if result and (result.startswith("Error") or result.startswith("Failure Recovery Error")):
            print(f"\033[91m{result}\033[0m")
            
        # Save updated active history to memory.json immediately
        save_session(session)

if __name__ == "__main__":
    main()
