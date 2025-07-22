# openproject-mcp/server.py
import httpx
import json
import base64
from fastmcp import FastMCP
from typing import List, Dict, Any

from config import logger, OPENPROJECT_API_KEY, OPENPROJECT_URL

mcp = FastMCP(name="OpenProject (ad-hoc) MCP Server")
client = httpx.AsyncClient(base_url=OPENPROJECT_URL, auth=("apikey", OPENPROJECT_API_KEY))


@mcp.tool
async def get_work_package_details(work_package_id: int) -> Dict[str, Any]:
    """
    Gets the full details of a specific work package, including its lockVersion,
    description, and other attributes.
    """
    logger.info(f"Tool executed: get_work_package_details(id={work_package_id})")
    response = await client.get(f"/api/v3/work_packages/{work_package_id}")
    response.raise_for_status()
    return response.json()


@mcp.tool
async def get_work_package_attachments(work_package_id: int) -> List[Dict[str, Any]]:
    """Lists all attachments for a given work package, returning their metadata (like ID and name)."""
    logger.info(f"Tool executed: get_work_package_attachments(id={work_package_id})")
    response = await client.get(f"/api/v3/work_packages/{work_package_id}/attachments")
    response.raise_for_status()
    return response.json().get("_embedded", {}).get("elements", [])


@mcp.tool
async def get_attachment_content(attachment_id: int) -> Dict[str, str]:
    """
    Gets the content of a single attachment by its ID. It fetches the
    attachment's metadata to find its download URL and MIME type, then downloads
    the raw content and returns it as a Base64 encoded string along with its
    MIME type.
    """
    logger.info(f"Tool executed: get_attachment_content(id={attachment_id})")

    # Step 1: Get attachment metadata to find the download URL and content type.
    try:
        meta_response = await client.get(f"/api/v3/attachments/{attachment_id}")
        meta_response.raise_for_status()
        attachment_data = meta_response.json()

        download_url = attachment_data["_links"]["downloadLocation"]["href"]
        file_name = attachment_data.get("fileName", "unknown_file")
        content_type = attachment_data.get("contentType", "application/octet-stream")

        logger.info(f"Found download URL for '{file_name}' (type: {content_type})")
    except (KeyError, httpx.HTTPStatusError) as e:
        logger.error(f"Could not retrieve metadata for attachment {attachment_id}: {e}")
        return {"mime_type": "text/plain",
                "data": f"[ERROR: Could not retrieve metadata for attachment {attachment_id}]"}

    # Step 2: Download the raw binary content
    try:
        content_response = await client.get(download_url)
        content_response.raise_for_status()
        file_bytes = content_response.content
    except Exception as e:
        logger.error(f"Failed to download content for attachment {attachment_id}: {e}")
        return {"mime_type": "text/plain", "data": f"[ERROR: Failed to download content for {file_name}]"}

    # Step 3: Encode the binary content in Base64 and return it in a structured way.
    base64_encoded_data = base64.b64encode(file_bytes).decode('utf-8')

    return {
        "mime_type": content_type,
        "data": base64_encoded_data
    }


@mcp.tool
async def update_work_package_description(work_package_id: int, lock_version: int, description: str) -> Dict[str, Any]:
    """Updates ONLY the description of a work package."""
    logger.info(f"Tool executed: update_work_package_description(id={work_package_id})")
    payload = {
        "lockVersion": lock_version,
        "description": {
            "raw": description,
            "format": "markdown"
        }
    }
    response = await client.patch(f"/api/v3/work_packages/{work_package_id}", json=payload)
    response.raise_for_status()
    return response.json()


@mcp.tool
async def update_work_package_status(work_package_id: int, lock_version: int, status_id: int) -> Dict[str, Any]:
    """Updates ONLY the status of a work package using a status ID."""
    logger.info(f"Tool executed: update_work_package_status(id={work_package_id}, status_id={status_id})")
    payload = {
        "lockVersion": lock_version,
        "_links": {
            "status": {
                "href": f"/api/v3/statuses/{status_id}"
            }
        }
    }
    response = await client.patch(f"/api/v3/work_packages/{work_package_id}", json=payload)
    response.raise_for_status()
    return response.json()


@mcp.tool
async def create_work_package_attachment(work_package_id: int, file_name: str, file_content: str,
                                         description: str = "") -> Dict[str, Any]:
    """Creates a new text file and attaches it to a work package."""
    logger.info(f"Tool executed: create_work_package_attachment for WP ID {work_package_id}")
    metadata = {
        "fileName": file_name,
        "description": {"raw": description}
    }
    files = {
        'metadata': (None, json.dumps(metadata), 'application/json'),
        'file': (file_name, file_content, 'text/plain')
    }
    response = await client.post(f"/api/v3/work_packages/{work_package_id}/attachments", files=files)
    response.raise_for_status()
    return response.json()


@mcp.tool
async def list_statuses() -> List[Dict[str, Any]]:
    """Lists all available work package statuses to find their names and IDs."""
    logger.info("Tool executed: list_statuses()")
    response = await client.get("/api/v3/statuses")
    response.raise_for_status()
    return response.json().get("_embedded", {}).get("elements", [])


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
