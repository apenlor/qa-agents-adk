# openproject_tools.py

import json
import importlib.resources as pkg_resources
from ..config import logger, OPENPROJECT_API_KEY, OPENPROJECT_URL
# ADK Tool Imports
from google.adk.tools.openapi_tool.openapi_spec_parser.openapi_toolset import OpenAPIToolset
from google.adk.tools.openapi_tool.auth.auth_helpers import token_to_scheme_credential
from google.adk.tools.base_tool import BaseTool


def _prepare_openapi_spec(spec_str: str, openproject_url: str) -> str:
    """Parses the OpenAPI spec string, injects the server URL, and returns the modified spec string."""
    spec_dict = json.loads(spec_str)
    if "servers" not in spec_dict:
        spec_dict["servers"] = []
    if not spec_dict["servers"]:
        spec_dict["servers"].append({"url": ""})
    spec_dict["servers"][0]["url"] = openproject_url
    return json.dumps(spec_dict)


def _initialize_openapi_toolset() -> OpenAPIToolset:
    """Loads the OpenAPI spec and initializes the toolset, or raises an error."""
    try:
        auth_scheme, auth_credential = token_to_scheme_credential(
            "apikey", "query", "apikey", OPENPROJECT_API_KEY
        )
        original_spec_str = pkg_resources.read_text('packages.tools', 'openproject-openapi-spec.json')
        spec_str = _prepare_openapi_spec(original_spec_str, OPENPROJECT_URL)
        logger.info("OpenAPI spec loaded successfully from packages.tools/openproject-openapi-spec.json")
        toolset = OpenAPIToolset(spec_str=spec_str, spec_str_type="json", auth_scheme=auth_scheme,
                                 auth_credential=auth_credential)
        logger.info("OpenAPIToolset initialized successfully.")
        return toolset
    except FileNotFoundError as e:
        logger.critical("CRITICAL: 'openproject-openapi-spec.json' not found. This is a required file.", exc_info=True)
        raise RuntimeError("Could not initialize OpenAPI toolset due to missing spec file.") from e
    except json.JSONDecodeError as e:
        logger.critical("CRITICAL: 'openproject-openapi-spec.json' is not a valid JSON file.", exc_info=True)
        raise RuntimeError("Could not initialize OpenAPI toolset due to invalid JSON.") from e
    except Exception as e:
        logger.critical(f"CRITICAL: Unexpected error initializing OpenAPIToolset: {e}", exc_info=True)
        raise RuntimeError("An unexpected error occurred during OpenAPI toolset initialization.") from e


# Initialize the critical OpenAPI toolset. The program will exit if this fails.
_OPENAPI_TOOLSET: OpenAPIToolset = _initialize_openapi_toolset()


async def get_all_tools() -> list[BaseTool]:
    return await _OPENAPI_TOOLSET.get_tools()


def find_tool(name: str) -> BaseTool | None:
    return _OPENAPI_TOOLSET.get_tool(name)
