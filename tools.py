import os
import re
from typing import Callable, Dict, Any

# Global registries for tools and their schemas
TOOL_REGISTRY: Dict[str, Callable] = {}
TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {}

def register_tool(name: str, description: str, parameters: Dict[str, Any]):
    """Decorator to register a function as an agent tool with a schema."""
    def decorator(func: Callable):
        TOOL_REGISTRY[name] = func
        TOOL_SCHEMAS[name] = {
            "name": name,
            "description": description,
            "parameters": parameters
        }
        return func
    return decorator

# --- Tool Definitions ---

@register_tool(
    name="calculate",
    description="Evaluate mathematical expressions securely using standard operators.",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The math expression to evaluate, e.g., '(45 * 82) + 120'. Only numbers and +, -, *, /, (, ) are allowed."
            }
        },
        "required": ["expression"]
    }
)
def calculate(expression: str) -> str:
    # Sanitize input: allow only basic numbers, operators, parentheses, and spaces
    clean_expression = re.sub(r'[^0-9+\-*/().\s]', '', expression)
    if clean_expression != expression:
        return f"Error: Expression contained forbidden characters. Raw: '{expression}', Sanitized: '{clean_expression}'"
    try:
        # Evaluate safely in a restricted scope
        result = eval(clean_expression, {"__builtins__": None}, {})
        return str(result)
    except Exception as e:
        return f"Error evaluating expression '{expression}': {str(e)}"

# Ensure notes directory exists
NOTES_DIR = "notes"
os.makedirs(NOTES_DIR, exist_ok=True)

@register_tool(
    name="write_note",
    description="Save a new text note locally on disk for persistent retrieval.",
    parameters={
        "type": "object",
        "properties": {
            "note_title": {
                "type": "string",
                "description": "Filename-safe title of the note, e.g., 'todo_list'."
            },
            "content": {
                "type": "string",
                "description": "The text content to save in the note."
            }
        },
        "required": ["note_title", "content"]
    }
)
def write_note(note_title: str, content: str) -> str:
    # Ensure filename is safe
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '', note_title)
    if not safe_title:
        return "Error: note_title is empty or contains only invalid characters."
    
    # Ensure notes directory exists at call-time
    os.makedirs(NOTES_DIR, exist_ok=True)
    filepath = os.path.join(NOTES_DIR, f"{safe_title}.txt")
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Success: Note saved successfully to {filepath}."
    except Exception as e:
        return f"Error writing note: {str(e)}"

@register_tool(
    name="read_notes",
    description="List and display all notes saved on disk.",
    parameters={
        "type": "object",
        "properties": {}
    }
)
def read_notes() -> str:
    try:
        if not os.path.exists(NOTES_DIR):
            return "No notes found (notes directory doesn't exist)."
        files = [f for f in os.listdir(NOTES_DIR) if f.endswith(".txt")]
        if not files:
            return "No notes found."
        
        output = []
        for filename in files:
            filepath = os.path.join(NOTES_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            title = filename[:-4]
            output.append(f"=== {title} ===\n{content}\n")
        return "\n".join(output)
    except Exception as e:
        return f"Error reading notes: {str(e)}"

@register_tool(
    name="search_facts",
    description="Search a mock database of general facts and project details.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Keywords to search the mock database for, e.g., 'Gemini API', 'population of Tokyo'."
            }
        },
        "required": ["query"]
    }
)
def search_facts(query: str) -> str:
    facts = {
        "tokyo": "The population of Tokyo metropolitan area is approximately 37.4 million people, making it the most populous metropolitan area in the world.",
        "gemini": "Gemini is a family of multimodal generative AI models developed by Google. The Gemini 1.5 Pro and Flash models support a context window of up to 2 million tokens.",
        "python": "Python was created by Guido van Rossum and first released in 1991. The name comes from the comedy group Monty Python.",
        "project schedule": "The deadline for the client delivery of Project Alpha is July 15, 2026. The milestone reviews are scheduled for June 20th and July 2nd."
    }
    
    query_lower = query.lower()
    matches = []
    for key, val in facts.items():
        if key in query_lower or query_lower in key:
            matches.append(f"- {key.capitalize()}: {val}")
    
    if matches:
        return "\n".join(matches)
    return f"No results found for query '{query}' in facts database."

def get_tool_definitions_string() -> str:
    """Returns a formatted string describing all available tools to pass to the system prompt."""
    import json
    lines = []
    for name, schema in TOOL_SCHEMAS.items():
        lines.append(f"Tool: '{name}'")
        lines.append(f"  Description: {schema['description']}")
        lines.append(f"  Parameters schema: {json.dumps(schema['parameters'], indent=4)}")
        lines.append("")
    return "\n".join(lines)

def execute_tool(name: str, arguments: Dict[str, Any]) -> str:
    """Executes a tool by name with the given arguments and returns a string observation."""
    if name not in TOOL_REGISTRY:
        raise ValueError(f"Tool '{name}' is not registered. Available tools: {list(TOOL_REGISTRY.keys())}")
    
    func = TOOL_REGISTRY[name]
    try:
        # Call the Python function unpacking the arguments dict
        result = func(**arguments)
        return str(result)
    except Exception as e:
        return f"Error executing tool '{name}': {str(e)}"
