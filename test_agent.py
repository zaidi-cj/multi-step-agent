import os
from memory import load_session, save_session
from agent import Agent

def run_test_query(query: str):
    print(f"\n==========================================")
    print(f"Testing Query: '{query}'")
    print(f"==========================================")
    
    # Load session
    session = load_session()
    
    # Initialize Agent
    agent = Agent(session)
    
    # Run loop
    response = agent.run(query)
    
    # Save session back
    save_session(session)
    print(f"\nResult: {response}")

def main():
    # Ensure starting fresh for tests
    if os.path.exists("memory.json"):
        os.remove("memory.json")
    if os.path.exists("notes"):
        import shutil
        shutil.rmtree("notes")
    
    # 1. Store name and preferences in Memory
    run_test_query("Hi, my name is Alice. I love coding in Python and my favorite color is emerald green. Can you greet me?")
    
    # 2. Retrieve persistent memory & Use Tools (Math)
    run_test_query("Calculate (45 * 8) + 140. Also, do you remember my name and favorite color?")
    
    # 3. Create a note (Tool Use)
    run_test_query("Write a note with title 'shopping_list' containing 'apples, milk, bananas'.")
    
    # 4. Read notes (Tool Use)
    run_test_query("Please read the notes I have saved on disk and tell me what is on my shopping list.")

    # 5. Summarize session and simulate exit persistence
    print("\n==========================================")
    print("Testing Session Summarization & Persistence")
    print("==========================================")
    session = load_session()
    agent = Agent(session)
    summary = agent.summarize_session()
    print(f"\nGenerated Conversation Summary:\n{summary}")
    
    # Save summary and clear active history (simulating session exit)
    session.summary_of_past_conversations = f"- {summary}"
    session.conversation_history = []
    save_session(session)
    
    # 6. Verify summary is loaded in a new session
    print("\n==========================================")
    print("Verifying New Session Load of Memory Context")
    print("==========================================")
    run_test_query("What items did we put on the shopping list in the last session?")

if __name__ == "__main__":
    main()
