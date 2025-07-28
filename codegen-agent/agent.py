# codegen-agent/agent.py
import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams
from google.genai.types import ToolConfig, GenerateContentConfig, FunctionCallingConfig, FunctionCallingConfigMode
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.readonly_context import ReadonlyContext

# --- POC Design Comment ---
# In this POC, we are giving the agent full control over the workflow to test
# its reasoning and tool-use capabilities, triggered by an API call.
# The agent will discover and orchestrate the necessary tools from the MCP server.
#
# In a production scenario, we might add more safety rails (like direct calls to
# the API for downloading attachments or performing the work package update), but for a
# POC, this approach demonstrates the full potential of an autonomous agent.

def _load_examples_as_text() -> str:
    """
    Reads example files from the 'examples' directory and formats them into a
    single string to be injected into the main instruction prompt.
    """
    example_files = [
        "examples/insurance.robot",
        "examples/mfa_login.robot",
        "examples/totp.py",
        "examples/restful_booker.robot",
        "examples/to_do.robot"
    ]
    all_examples_text = ""
    for file_path in example_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Use Markdown code blocks for clear separation and language hinting.
                file_extension = os.path.splitext(file_path)[1].strip('.')
                all_examples_text += f"--- Example File: {os.path.basename(file_path)} ---\n"
                all_examples_text += f"```{file_extension}\n"
                all_examples_text += content
                all_examples_text += "\n```\n\n"
        except FileNotFoundError:
            print(f"Warning: Example file not found at {file_path}. It will be omitted from the prompt.")
    return all_examples_text


INSTRUCTION_TEMPLATE = """
You are an expert QA Automation Engineer specializing in Robot Framework.

**Your Mission:**
You will be given a work package ID. Your mission is to read its requirements (description and acceptance criteria) and generate a complete, functional Robot Framework test file that covers those requirements, following all project-specific conventions and examples.

---
**REFERENCE EXAMPLES**
Here are examples of high-quality test files from our project. Use them to understand the required structure, style, and keywords.

{code_examples}
---

**High-Level Workflow & Tool Guide:**
1.  **Read Requirements:** Use `get_work_package_details` to fetch the work package's `description` and acceptance criteria.
2.  **Generate Test Suite:** Write a complete Robot Framework test suite (`.robot` file content).
    - Start with a `*** Settings ***` section, including necessary `Library` imports based on the examples.
    - Create `*** Test Cases ***`. For each acceptance criterion, create one Test Case.
    - If needed, create `*** Keywords ***` for reusable logic like authentication.
3.  **Attach Test File:** Use `create_work_package_attachment` to attach the generated code. Use a filename like `test_case_for_wp_{{work_package_id}}.robot`.
4.  **Update Status:** Use `list_statuses` and `update_work_package_status` to move the work package to the 'In testing' status.
5.  **Final Step:** Call `exit_loop` with a summary of your work.
"""

# -- Build the codegen agent, loading examples from disk and injecting them into the instruction prompt.
required_tools = [
    "get_work_package_details",
    "create_work_package_attachment",
    "list_statuses",
    "update_work_package_status",
]
toolset = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(url="http://openproject-mcp:8000/mcp/"),
    tool_filter=required_tools
)


def exit_loop(summary: str, tool_context: ToolContext):
    """Call this as the final step to complete the mission."""
    tool_context.actions.escalate = True
    return {"status": "complete", "summary": summary}


# Configure the LLM to return control after each tool call.
tool_config = ToolConfig(function_calling_config=FunctionCallingConfig(mode=FunctionCallingConfigMode.ANY))
generate_content_config = GenerateContentConfig(tool_config=tool_config)


# Assemble the final instruction prompt by injecting the examples.
def instruction_provider(ctx: ReadonlyContext) -> str:
    code_examples = _load_examples_as_text()
    return INSTRUCTION_TEMPLATE.format(code_examples=code_examples)


# Create and return the agent instance.
codegen_agent = LlmAgent(
    name="codegen_agent_v1",
    model="gemini-2.5-pro",
    description="Generates advanced Robot Framework tests from work package requirements.",
    instruction=instruction_provider,
    tools=[toolset, exit_loop],
    generate_content_config=generate_content_config
)

print(f"Agent '{codegen_agent.name}' created with file-based examples.")
