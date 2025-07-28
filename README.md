# QE Agents ADK - Testing code generation

This repository contains a Proof of Concept (POC) for integrating AI agents with an OpenProject instance. It features a
custom MCP server and two autonomous agents built with
the [Google Agent Development Kit](https://google.github.io/adk-docs/) (ADK).

* The Analysis Agent reads requirements from work package attachments (text, pdf or images), generates a description and
  acceptance criteria, and updates the work package's status to 'Specified'.
* The Codegen Agent reads the updated requirements, generates a Robot Framework test suite, attaches it to the work
  package, and updates the status to 'In testing'.

## Prerequisites

To run this proof of concept, you will need the following software installed on your machine:

* **Docker**
* **Docker Compose**
* **cURL** or a similar API client.

## Setup and Configuration

Follow these steps to configure and run the entire stack.

### 1. Get the OpenProject API Key

1. **Start OpenProject service**: Run the following command to start just the OpenProject container.
    ```bash
      docker-compose up -d openproject
    ```
2. **Log in and generate key**:
    * Wait for the service to become healthy.
         ```bash 
         docker-compose ps
         ```
    * Navigate to `http://localhost:8080`.
    * Log in with `admin / admin` and change the password.
    * Navigate to your user avatar (top-right) -> `Account Settings` -> `Access Tokens`.
    * Under the API section, click Generate and copy the key.

### 2. Configure the environment variables

Both the MCP server and the agents require creating the following `.env` files:

#### MCP Server

1. Create the file:
    ```bash 
    touch openproject-mcp/.env
    ```
2. Add your OpenProject API key
    ```txt
    OPENPROJECT_API_KEY="YOUR_OPENPROJECT_API_KEY"
    OPENPROJECT_URL=http://openproject-proxy:80
    ```

#### Agents

1. Create the files:
    ```bash 
    touch analysis-agent/.env
    touch codegen-agent/.env
   ```
2. Add your Google AI API key to both files:
    ```txt 
    # Get this key from Google AI Studio: https://aistudio.google.com/app/apikey
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
   ```

### 3. Required OpenProject configuration

For the agents to function correctly, perform these one-time setup steps while logged in as `admin`.

#### Configure OpenProject Workflows

Only two statuses are required: `Specified` and `In testing`. But for simplicity, all statuses will be enabled.

1. Navigate to `Administration` (from your avatar dropdown).
2. On the menu, go to `Work Pakages` -> `Workflows`.
3. In the table, find the row for the Role `Member` and the Type `Task`.
4. Click the `Edit` button.
5. Use the `Check all` at the top of the table to get all status checks activated.
6. Click Save.
7. Repeat steps 4-6 for the roles `Reader` and `Project admin` for the `Task` type.

## Running the full stack

With all configurations in place, launch all services.

```bash 
  docker-compose up --build -d
```

You can monitor the logs of the agents and MCP server with:

```bash 
  docker-compose logs -f analysis-agent codegen-agent openproject-mcp
```

## E2E Testing Workflow

This guide walks through the manual process of creating a work package and triggering the agents.

### Step 1: Create and Prepare the Work Package

1. **Create a Task**: In the OpenProject UI (http://localhost:8080), go to a project and create a new Task. Give it a
   subject like "Test Full Agent Workflow".
2. **Add Attachments**: Go to the `Files` tab of the new work package. Upload one or more files from the
   `./test_attachments/` directory (e.g., `technical_spec_checksum.txt`).

### Step 2: Trigger the Analysis Agent

The Analysis Agent's job is to read the attachments and update the description and status.

1. **Get the Work Package ID**: Note the ID of the work package you just created from the URL or the title (e.g., #37).
2. **Trigger the Agent**: Open your terminal and run the following curl command, replacing <YOUR_WP_ID> with the actual
   ID.
   ```bash
      curl -X POST http://localhost:8081/analyse-work-package \
      -H "Content-Type: application/json" \
      -d '{"work_package_id": <YOUR_WP_ID>}'
   ```
3. **Verify the Result**:
    * Check the agent's logs
      ```bash
         docker-compose logs -f analysis-agent
      ```
    * Refresh the work package in OpenProject. The Description should now be filled with the agent's analysis, and the
      Status should be `Specified`.

### Step 3: Trigger the Codegen Agent

The Codegen Agent takes the new description and acceptance criteria to generate test code.

1. **Trigger the Agent**: Run the following `curl` command, using the same work package ID.
   ```bash
      curl -X POST http://localhost:8082/generate-code \
      -H "Content-Type: application/json" \
      -d '{"work_package_id": <YOUR_WP_ID>}'
   ```
2. **Verify the Result**:
    * Check the agent's logs
      ```bash
         docker-compose logs -f codegen-agent
      ```
    * Refresh the work package. A new file (e.g., `acceptance_tests.robot`) should now be in the files tab, and the
      Status should be `In testing`

## Project Structure

Here is a breakdown of the key files and directories in this repository.

```txt
   .
   ├── README.md
   ├── analysis-agent
   │         ├── Dockerfile
   │         ├── agent.py
   │         ├── config.py
   │         ├── examples
   │         │         ├── tech_requirements_example.md
   │         │         └── user_feature_example.md
   │         ├── logger_utils.py
   │         ├── main.py
   │         ├── requirements.txt
   │         └── runner.py
   ├── codegen-agent
   │         ├── Dockerfile
   │         ├── agent.py
   │         ├── config.py
   │         ├── examples
   │         │         ├── insurance.robot
   │         │         ├── mfa_login.robot
   │         │         ├── restful_booker.robot
   │         │         ├── to-do.robot
   │         │         └── totp.py
   │         ├── logger_utils.py
   │         ├── main.py
   │         ├── requirements.txt
   │         └── runner.py
   ├── docker-compose.yml
   ├── openproject-mcp
   │         ├── Dockerfile
   │         ├── config.py
   │         ├── mcp_openapi_server.py
   │         ├── openapi_loader.py
   │         ├── proxy
   │         │         └── nginx.conf
   │         ├── requirements.txt
   │         ├── server.py
   │         └── tests
   │             ├── requirements.txt
   │             └── test_mcp_server.py
   └── test_attachments
       ├── bug_report_profile_picture.txt
       ├── technical_spec_checksum.txt
       └── user_story_login.txt

```

#### Root Directory

* [`docker-compose.yml`](./docker-compose.yml): The main orchestration file. It defines all the services (OpenProject,
  MCP, agents), their build configurations, networks, and dependencies.
* [`test_attachments/`](./test_attachments/): Contains example `.txt` files with requirement specifications. These are
  intended to be manually uploaded to an OpenProject work package to test the end-to-end agent workflow.

#### OpenProject MCP Server (`openproject-mcp/`)

This service acts as an intelligent, ad-hoc API gateway between the agents and the OpenProject instance.

* [`server.py`](./openproject-mcp/server.py): The core of the MCP. It's a `FastMCP` application that defines a set of
  curated, high-level tools (e.g., `update_work_package_status`). It simplifies the OpenProject API for the agents and
  handles complexities like authentication and optimistic locking.
* [`proxy/nginx.conf`](./openproject-mcp/proxy/nginx.conf): An Nginx configuration used to create a reverse proxy that
  solves an internal hostname resolution issue with the OpenProject container.
* [`Dockerfile`](./openproject-mcp/Dockerfile): Instructions to build the container image for the MCP server.

#### Analysis Agent (`analysis-agent/`)

An autonomous agent service responsible for analyzing requirements.

* [`main.py`](./analysis-agent/main.py): The entry point of the service. It's a `FastAPI` application that exposes a
  single webhook endpoint (`/analyse-work-package`) to receive triggers. It manages the application lifecycle, including
  the creation of the agent instance.
* [`agent.py`](./analysis-agent/agent.py): Defines the `LlmAgent` itself. This is where the agent's persona, core
  instructions, and toolset are configured. It includes the detailed prompt and "few-shot" examples that guide the
  agent's behavior.
* [`runner.py`](./analysis-agent/runner.py): Contains the orchestration logic. The `execute_analysis` function is called
  by the API endpoint to manage the agent's execution, handle the event stream, and log the agent's "thoughts" and
  actions.
* [`logger_utils.py`](./analysis-agent/logger_utils.py): A helper module containing functions to format the agent's
  event stream into human-readable log messages.

#### Codegen Agent (`codegen-agent/`)

An autonomous agent service for generating test code. Its structure and file responsibilities are identical to those of
the `analysis-agent`.

## Architectural Notes

### OpenProject Proxy

A Nginx proxy is placed between the MCP server and the main OpenProject instance. This is necessary to resolve a
hostname conflict. The OpenProject application, when running in Docker, internally redirects certain API requests to its
configured `OPENPROJECT_HOST__NAME` (localhost:8080). This localhost address is unreachable from another container. The
proxy intercepts these requests and correctly forwards them to the openproject service name within the Docker network.

### Ad-hoc vs. OpenAPI MCP Server

The primary MCP server (`server.py`) is an ad-hoc implementation. It defines a curated, stable set of tools specifically
for the agents' needs. This approach was chosen for its robustness and simplicity after encountering inconsistencies in
the official OpenProject OpenAPI specification (spec.json). Also, the agents got a little overwhelmed by having the
whole API available for tools.

For academic interest, the alternative server based on parsing this OpenAPI spec (mcp_openapi_server.py) is included but
is deprecated and not recommended for use.

### Future Work & Next Steps

### Automated webhook integration

The ideal workflow for this POC is to have the agents triggered automatically by status changes in OpenProject via
webhooks. This was postponed due to limitations in the OpenProject webhook system, which sends a fixed payload and lacks
fine-grained event filtering (e.g., "trigger only when status changes to X").

To implement this, the agent endpoints would need to be updated to:

1. Accept the full, default OpenProject webhook payload.
2. Parse the payload to find the "before" and "after" status.
3. Contain internal logic to act only when the status changes to the desired trigger state (e.g., `In specification` for
   the analysis agent, `Confirmed` for the codegen agent).
