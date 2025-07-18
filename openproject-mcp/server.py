# openproject-mcp/server.py
import httpx
from fastmcp import FastMCP
from config import logger, OPENPROJECT_API_KEY, OPENPROJECT_URL
from openapi_loader import load_and_patch_spec

patched_spec = load_and_patch_spec()
client = httpx.AsyncClient(base_url=OPENPROJECT_URL, auth=("apikey", OPENPROJECT_API_KEY))
mcp = FastMCP.from_openapi(
    openapi_spec=patched_spec,
    client=client,
    name="OpenProject MCP Server (FastMCP)"
)

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)