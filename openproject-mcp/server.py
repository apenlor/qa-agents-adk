# openproject-mcp/server.py
import httpx
import json
import base64
import fitz
from fastmcp import FastMCP
from typing import List, Dict, Any

from fastmcp.tools.tool import ToolResult
from mcp.types import ImageContent, TextContent

from config import logger, OPENPROJECT_API_KEY, OPENPROJECT_URL

mcp = FastMCP(name="OpenProject (ad-hoc) MCP Server")
client = httpx.AsyncClient(base_url=OPENPROJECT_URL, auth=("apikey", OPENPROJECT_API_KEY))


async def _get_raw_work_package_details(work_package_id) -> Dict[str, Any]:
    logger.debug(f"Fetching raw details for work package ID: {work_package_id}")
    response = await client.get(f"/api/v3/work_packages/{work_package_id}")
    response.raise_for_status()
    return response.json()


@mcp.tool
async def get_work_package_details(work_package_id: int) -> Dict[str, Any]:
    """
    Gets a filtered, essential set of details for a specific work package.
    """
    full_wp = await _get_raw_work_package_details(work_package_id)
    filtered_details = {
        "id": full_wp.get("id"),
        "subject": full_wp.get("subject"),
        "lockVersion": full_wp.get("lockVersion"),
        "description": full_wp.get("description", {}).get("raw"),
        "status": full_wp.get("_embedded", {}).get("status", {}).get("name"),
    }
    logger.info(f"Tool Success: get_work_package_details -> Returning filtered details for WP {work_package_id}")
    return filtered_details


@mcp.tool
async def get_work_package_attachments(work_package_id: int) -> List[Dict[str, Any]]:
    """Lists all attachments for a given work package, returning their metadata (like ID and name)."""
    logger.info(f"Tool executed: get_work_package_attachments(id={work_package_id})")
    response = await client.get(f"/api/v3/work_packages/{work_package_id}/attachments")
    response.raise_for_status()
    return response.json().get("_embedded", {}).get("elements", [])


@mcp.tool
async def get_attachment_content(attachment_id: int) -> ToolResult:
    """
    Gets the content of an attachment.
    - For images, returns an ImageContent block.
    - For PDFs, extracts both text and images, returning a list of TextContent
      and ImageContent blocks.
    - For other files, returns a TextContent block.
    """
    logger.info(f"Tool executed: get_attachment_content(id={attachment_id})")
    try:
        meta_response = await client.get(f"/api/v3/attachments/{attachment_id}")
        meta_response.raise_for_status()
        attachment_data = meta_response.json()
        download_url = attachment_data["_links"]["downloadLocation"]["href"]
        file_name = attachment_data.get("fileName", "unknown_file")
        content_type = attachment_data.get("contentType", "application/octet-stream")
        content_response = await client.get(download_url)
        content_response.raise_for_status()
        file_bytes = content_response.content

        content_blocks = []

        if content_type.endswith('pdf'):
            logger.info(f"'{file_name}' is a PDF. Extracting multi-modal content...")
            extracted_text = f"--- Extracted Text from PDF: {file_name} ---\n\n"
            image_count = 0
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                for page_num, page in enumerate(doc):
                    extracted_text += f"\n--- Page {page_num + 1} ---\n"
                    extracted_text += page.get_text() + "\n"

                    for img_index, img in enumerate(page.get_images(full=True)):
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]

                        content_blocks.append(ImageContent(
                            data=base64.b64encode(image_bytes).decode('utf-8'),
                            mimeType=f"image/{image_ext}",
                            type="image"
                        ))
                        image_count += 1

            content_blocks.insert(0, TextContent(text=extracted_text, type="text"))
            logger.info(f"Extracted {len(extracted_text)} chars and {image_count} images from PDF.")

        elif content_type.startswith('image/'):
            logger.info(f"Returning ImageContent for '{file_name}'.")
            base64_data = base64.b64encode(file_bytes).decode('utf-8')
            content_blocks.append(ImageContent(data=base64_data, mimeType=content_type, type="image"))

        else:
            logger.info(f"Returning TextContent for '{file_name}'.")
            text_content = file_bytes.decode('utf-8', errors='replace')
            content_blocks.append(TextContent(text=text_content, type="text"))

        return ToolResult(content=content_blocks)

    except Exception as e:
        logger.error(f"Failed to get attachment content for ID {attachment_id}: {e}", exc_info=True)
        return ToolResult(content=[TextContent(text=f"[ERROR: Could not process attachment {attachment_id}]")])


@mcp.tool
async def update_work_package_description(work_package_id: int, description: str) -> Dict[str, Any]:
    """
    Updates ONLY the description of a work package.
    Handles technical details like lockVersion automatically.
    Returns a simple success confirmation message upon completion.
    This is a final action; do not call other tools to verify after using this one.
    """
    logger.info(f"Tool Action: update_work_package_description(id={work_package_id})")
    latest_wp = await _get_raw_work_package_details(work_package_id)
    payload = {
        "lockVersion": latest_wp["lockVersion"],
        "description": {"raw": description, "format": "markdown"}
    }
    response = await client.patch(f"/api/v3/work_packages/{work_package_id}", json=payload)
    response.raise_for_status()
    updated_wp = response.json()
    return {
        "status": "Success",
        "message": "Description updated.",
        "newLockVersion": updated_wp.get("lockVersion")
    }


@mcp.tool
async def update_work_package_status(work_package_id: int, status_id: int) -> Dict[str, Any]:
    """
    Updates ONLY the status of a work package to a new status ID.
    Handles technical details like lockVersion automatically.
    Returns a simple success confirmation message upon completion.
    This is a final action; do not call other tools to verify after using this one.
    """
    logger.info(f"Tool Action: update_work_package_status(id={work_package_id}, status_id={status_id})")
    latest_wp = await _get_raw_work_package_details(work_package_id)
    payload = {
        "lockVersion": latest_wp["lockVersion"],
        "_links": {"status": {"href": f"/api/v3/statuses/{status_id}"}}
    }
    response = await client.patch(f"/api/v3/work_packages/{work_package_id}", json=payload)
    response.raise_for_status()
    updated_wp = response.json()
    return {
        "status": "Success",
        "message": "Status updated.",
        "newLockVersion": updated_wp.get("lockVersion")
    }


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
