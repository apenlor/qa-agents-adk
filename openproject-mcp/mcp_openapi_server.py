# openproject-mcp/mcp_openapi_server.py
import httpx
from fastmcp import FastMCP
from config import logger, OPENPROJECT_API_KEY, OPENPROJECT_URL
from openapi_loader import load_and_patch_spec

# --- DEPRECATION NOTICE ---
# This OpenAPI-based server is not recommended for production use.
#
# The official OpenProject OpenAPI specification contains structural errors
# that cannot be fully corrected by our patching mechanism. These underlying
# issues prevent FastMCP from generating a consistently reliable toolset,
# which can lead to unexpected runtime failures.
#
# For a stable and reliable implementation, please use `server.py` instead.
# It provides a manually curated and tested set of tools for OpenProject.
# --------------------------

patched_spec = load_and_patch_spec()
client = httpx.AsyncClient(base_url=OPENPROJECT_URL, auth=("apikey", OPENPROJECT_API_KEY))
mcp = FastMCP.from_openapi(
    openapi_spec=patched_spec,
    client=client,
    name="OpenProject (OpenAPI based) MCP Server"
)

if __name__ == "__main__":
    logger.warning(
        "DEPRECATION WARNING: You are running the OpenAPI-based MCP server. "
        "This server is unstable due to issues in the source OpenAPI spec and may fail unexpectedly. "
        "It is strongly recommended to use 'server.py' instead for reliable operation."
    )
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)