# openproject-mcp/openapi_loader.py
import httpx
from typing import Iterator
from config import logger, OPENPROJECT_API_KEY, OPENPROJECT_URL

def _patch_group_model(spec: dict) -> dict:
    """
    Applies a critical structural patch for the GroupModel in the OpenAPI spec.

    This patch is required for some tools to parse the spec correctly. It fixes
    an issue where GroupModel._embedded.members.items is a list `[{...}]`
    instead of the expected object `{...}`.
    """
    try:
        members_property = (
            spec['components']['schemas']['GroupModel']['allOf'][1]
            ['properties']['_embedded']['properties']['members']
        )
        if isinstance(members_property.get('items'), list) and len(members_property['items']) == 1:
            logger.info("Applying critical structural patch to GroupModel.members.items...")
            # Replace the list with the object it contains.
            members_property['items'] = members_property['items'][0]
    except (KeyError, IndexError, TypeError) as e:
        logger.warning(
            "Could not apply critical GroupModel patch. The spec might be invalid or has changed. "
            f"Proceeding without it. Error: {e}"
        )
    return spec

def _get_properties_from_schema(schema_definition: dict) -> Iterator[dict]:
    """
    Yields all top-level property dictionaries from a schema definition,
    including those nested directly within an 'allOf' block.
    """
    if 'properties' in schema_definition:
        yield schema_definition['properties']

    if 'allOf' in schema_definition:
        for sub_schema in schema_definition.get('allOf', []):
            if isinstance(sub_schema, dict) and 'properties' in sub_schema:
                yield sub_schema['properties']

def _make_property_nullable(prop_details: dict) -> None:
    """
    Modifies a single property definition dictionary in-place to make it nullable.

    It checks if the property is a valid, non-reference type before modification.
    If the property's type is not already a list, it's converted to one.
    Finally, 'null' is added to its list of allowed types.
    """
    # Ensure we're modifying a property object that has a 'type' and is not a reference.
    if not (isinstance(prop_details, dict) and 'type' in prop_details and '$ref' not in prop_details):
        return

    current_type = prop_details['type']

    # Normalize type to a list to simplify logic
    if not isinstance(current_type, list):
        current_type = [current_type]

    # Add 'null' to the list of allowed types if not already present
    if 'null' not in current_type:
        prop_details['type'] = current_type + ['null']

def _patch_make_all_properties_nullable(spec: dict) -> dict:
    """
    Makes all schema properties in the OpenAPI spec nullable.

    This is an aggressive strategy to avoid validation errors during
    Proof of Concept (POC) development. It iterates through all schemas and
    delegates the modification of each property to the `_make_property_nullable`
    helper function.
    """
    logger.warning("Applying aggressive patch: Making all schema properties nullable.")

    schemas = spec.get('components', {}).get('schemas', {})
    if not schemas:
        logger.error("Spec does not contain 'components.schemas'. Cannot apply nullable patch.")
        return spec

    for schema_definition in schemas.values():
        for properties_block in _get_properties_from_schema(schema_definition):
            for prop_details in properties_block.values():
                _make_property_nullable(prop_details)

    return spec

def _patch_remove_problematic_required_fields(spec: dict) -> dict:
    """
    Removes specific fields from the 'required' list of their schemas.

    This patch targets fields that the OpenAPI spec declares as required, but
    the API sometimes omits from the response, causing validation errors.
    """
    logger.info("Applying patch to remove problematic 'required' fields...")
    schemas = spec.get('components', {}).get('schemas', {})

    def _remove_from_required(schema_def: dict, field_name: str, model_name: str):
        """Helper to remove a field from 'required' lists, including in 'allOf'."""
        lists_to_check = []
        if 'required' in schema_def:
            lists_to_check.append(schema_def['required'])
        for sub_schema in schema_def.get('allOf', []):
            if isinstance(sub_schema, dict) and 'required' in sub_schema:
                lists_to_check.append(sub_schema['required'])

        for req_list in lists_to_check:
            if field_name in req_list:
                req_list.remove(field_name)
                logger.debug(f"Removed '{field_name}' from 'required' list in {model_name}.")

    try:
        # Error: "'title' is a required property" for list_work_package_attachments
        # The response items for this tool are of type AttachmentModel.
        _remove_from_required(schemas['AttachmentModel'], 'title', 'AttachmentModel')

        # Error: "'children' is a required property" for view_work_package
        # The 'children' field is in the '_links' object of the WorkPackageModel.
        work_package_links_schema = schemas['WorkPackageModel']['properties']['_links']
        _remove_from_required(work_package_links_schema, 'children', 'WorkPackageModel._links')

        # Error: "{'algorithm': 'md5', ...} is not of type 'string', 'null'"
        digest_property = schemas['AttachmentModel']['properties']['digest']
        logger.info("Applying patch to AttachmentModel.digest to change type to 'object'...")
        digest_property['type'] = ['object', 'null']
        _remove_from_required(schemas['AttachmentModel'], 'digest', 'AttachmentModel')
    except KeyError as e:
        logger.error(f"Could not apply 'required' field patch. Schema structure may have changed. Error: {e}")

    return spec

def _patch_spec(spec: dict) -> dict:
    """
     Internal function to apply multiple, sequential patches to the OpenAPI spec.
     """
    logger.info("Applying patches to the OpenAPI spec...")
    spec = _patch_group_model(spec)
    spec = _patch_remove_problematic_required_fields(spec)
    spec = _patch_make_all_properties_nullable(spec)
    logger.info("Finished applying all patches to the spec.")
    return spec

def load_and_patch_spec() -> dict:
    """
    Fetches the OpenAPI spec from the server, applies necessary patches,
    and returns the corrected spec as a dictionary.
    """
    spec_url = f"{OPENPROJECT_URL}/api/v3/spec.json"
    logger.info(f"Fetching OpenAPI spec from {OPENPROJECT_URL}/api/v3/spec.json")
    try:
        response = httpx.get(
            spec_url,
            auth=("apikey", OPENPROJECT_API_KEY)
        )
        response.raise_for_status()
        openapi_spec = response.json()
        logger.info("OpenAPI spec fetched successfully.")

        # Apply patches sequentially
        return _patch_spec(openapi_spec)

    except httpx.HTTPStatusError as e:
        logger.critical(
            f"Failed to fetch OpenAPI spec. Status: {e.response.status_code}. "
            f"Response: {e.response.text}"
        )
        raise RuntimeError("Could not fetch OpenAPI spec due to an HTTP error.") from e
    except Exception as e:
        logger.critical(f"An unexpected error occurred while fetching/patching the OpenAPI spec: {e}")
        raise RuntimeError("Failed to prepare OpenAPI spec.") from e