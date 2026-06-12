import json
import os
from schemas import SessionState

MEMORY_FILE = "memory.json"

def load_session(filepath: str = MEMORY_FILE) -> SessionState:
    """Loads the agent's persistent memory state from a JSON file."""
    if not os.path.exists(filepath):
        return SessionState()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return SessionState.model_validate(data)
    except Exception as e:
        print(f"\n[Memory System] Warning: Failed to load memory from {filepath} ({e}). Starting fresh.")
        return SessionState()

def save_session(session: SessionState, filepath: str = MEMORY_FILE) -> None:
    """Saves the agent's memory state to a JSON file."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            # Serializes session data validated by Pydantic
            json.dump(session.model_dump(), f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"\n[Memory System] Error: Failed to save memory to {filepath}: {e}")
