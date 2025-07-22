# ./openproject-mcp/config.py

import logging
import os
from dotenv import load_dotenv

load_dotenv()
# Set default log level to INFO, but allow overriding via environment variable.
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("analysis-agent-logger")
# --- SILENCE NOISY LIBRARY LOGS ---
logging.getLogger("google_adk.google.adk.tools.base_authenticated_tool").setLevel(logging.ERROR)
logging.getLogger("google_adk.google.adk.models.google_llm").setLevel(logging.WARNING)
logging.getLogger("google_genai.types").setLevel(logging.ERROR)

def _get_required_env(var_name: str) -> str:
    """Gets a required environment variable, raising an error if not found."""
    value = os.getenv(var_name)
    if not value:
        error_msg = f"CRITICAL ERROR: Environment variable '{var_name}' is not set."
        logger.critical(error_msg)
        raise ValueError(error_msg)
    return value

# Load and validate required environment variables for Google AI
GEMINI_API_KEY = _get_required_env("GEMINI_API_KEY")

logger.info("Configuration loaded and Gemini API Key is set.")
