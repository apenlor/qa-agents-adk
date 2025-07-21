# ./openproject-mcp/config.py

import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("analysis-agent-logger")

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
