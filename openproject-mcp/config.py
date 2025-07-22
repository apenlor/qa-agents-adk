# ./openproject-mcp/config.py

import logging
import os
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("openproject-mcp-logger")

def _get_required_env(var_name: str, placeholder: str | None = None) -> str:
    """Gets a required environment variable, exiting if not found or a placeholder."""
    value = os.getenv(var_name)
    if not value or (placeholder and value == placeholder):
        error_msg = (
            f"CRITICAL ERROR: Environment variable '{var_name}' is not set "
            f"or contains a placeholder value. Please set it correctly in your .env file."
        )
        logger.critical(error_msg)
        raise ValueError(error_msg)
    return value

load_dotenv()

# Load and validate required environment variables
OPENPROJECT_API_KEY = _get_required_env("OPENPROJECT_API_KEY", placeholder="API_KEY_HERE")
OPENPROJECT_URL = _get_required_env("OPENPROJECT_URL")

logger.info("Configuration and environment variables loaded successfully.")
