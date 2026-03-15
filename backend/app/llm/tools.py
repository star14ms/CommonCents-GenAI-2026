"""OpenAI-compatible tools available for chat. Used when provider supports them (e.g. ChatGPT).

See: https://developers.openai.com/api/docs/guides/tools/
"""

import os


def _file_search_config() -> dict:
    """Build file_search config from OPENAI_VECTOR_STORE_IDS env (comma-separated)."""
    ids = [x.strip() for x in os.environ.get("OPENAI_VECTOR_STORE_IDS", "").split(",") if x.strip()]
    return {"type": "file_search", "vector_store_ids": ids}


AVAILABLE_TOOLS = [
    {
        "id": "web_search",
        "name": "Web Search",
        "description": "Include data from the Internet in model response generation. Use for news, real-time data, or facts beyond the model's training.",
        "config": {"type": "web_search"},
    },
    {
        "id": "code_interpreter",
        "name": "Code Interpreter",
        "description": "Run Python code in a sandbox. Use for calculations, data analysis, charts, or file processing.",
        "config": {"type": "code_interpreter"},
    },
    {
        "id": "file_search",
        "name": "File Search",
        "description": "Search the contents of uploaded files for context. Set OPENAI_VECTOR_STORE_IDS (comma-separated) to enable.",
        "config_factory": _file_search_config,
    },
    {
        "id": "tool_search",
        "name": "Tool Search",
        "description": "Dynamically load relevant tools into the model's context. Requires gpt-5.4 or later.",
        "config": {"type": "tool_search"},
    },
]
