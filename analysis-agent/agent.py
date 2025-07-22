from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams
from google.adk.agents import LlmAgent
from google.genai.types import ToolConfig, GenerateContentConfig, FunctionCallingConfig, FunctionCallingConfigMode

# --- POC Design Comment ---
# In this POC, we are giving the agent full control over the workflow to test
# its reasoning and tool-use capabilities, triggered by an API call.
# The agent will discover and orchestrate the necessary tools from the MCP server.
#
# In a production scenario, we might add more safety rails (like direct calls to
# the API for downloading attachments or performing the work package update), but for a
# POC, this approach demonstrates the full potential of an autonomous agent.


# Initializes ToolSet
toolset = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="http://openproject-mcp:8000/mcp/",
    )
)
# Create the tool configuration to disable the model's automatic loop
tool_config = ToolConfig(function_calling_config=FunctionCallingConfig(
    mode=FunctionCallingConfigMode.ANY
))

analysis_agent = LlmAgent(
    name="analysis_agent_v1",
    model="gemini-2.5-flash",
    description="An autonomous agent that analyzes, updates, and transitions OpenProject work packages.",
    instruction="""
    You are an autonomous Senior Business Analyst. Your goal is to process an OpenProject work package by following the detailed steps for execution. You will only execute one iteration of these steps. Concluding with a final output that must be a single, brief sentence summarizing the work done. 
    
    **Steps for execution:**
    1.  Use `get_work_package_attachments` to find attachments for the given work package ID.
    2.  Use `get_attachment_content` to read the content of all found attachments. If there are no attachments, your final response must be "No attachments found for work package [ID]. Cannot proceed."
    3.  Based on the attachment contents, that can either be image or text, formulate a new `description` and `acceptance_criteria`.
    4.  Call `update_work_package_description` with the new description. If response contains "Success", the step is complete.
    5.  Call `list_statuses` to find the numerical ID for the "Specified" status.
    6.  Call `update_work_package_status` with the work package ID and the status ID you found. If response contains "Success", the step is complete.
    """,
    tools=[toolset],
    generate_content_config=GenerateContentConfig(tool_config=tool_config)
)

print(f"Agent '{analysis_agent.name}' created with full MCP toolset.")
