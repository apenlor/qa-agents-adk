# QE Agents ADK

This repository contains a Proof of Concept (POC) for integrating QE agents with an OpenProject instance. It features a custom MCP (Model Context Protocol) server built with `FastMCP` that exposes the OpenProject API as a set of tools for consumption by AI agents.

## Prerequisites

To run this proof of concept, you will need the following software installed on your machine:

*   **Docker**
*   **Docker Compose**
*   **Python 3.10+** (for running the test script)
*   **pip** (for installing test dependencies)

## Getting Started

Follow these steps to configure and run the entire stack.

### 1. Initial Setup: Get the OpenProject API Key

The MCP server requires an API key to communicate with the OpenProject instance. The best way to get this key is to start *only* the OpenProject container first.

1.  **Start OpenProject Service**: Run the following command to start just the OpenProject container, ignoring the other services for now.
    ```bash
    docker-compose up -d openproject
    ```

2.  **Log In and Generate Key**:
    *   Wait a minute for the service to become healthy (`docker-compose ps` should show it as `healthy`).
    *   Navigate to `http://localhost:8080` in your browser.
    *   Log in with the default credentials: `admin` / `admin`. You will be prompted to change the password.
    *   Once logged in, navigate to your user avatar (top-right) -> **Account Settings** -> **Access Tokens**.
    *   Under the **API** section, click **Generate**.
    *   **Copy the generated API key**. You will need it in the next step.

3.  **Stop the Container**: This will stop the OpenProject service.
    ```bash
    docker-compose down
    ```

### 2. Configure the Environment

Create a `.env` file for the MCP server and add the API key you just generated.

1.  **Create the file**:
    ```bash
    touch openproject-mcp/.env
    ```

2.  **Add the following content** to `openproject-mcp/.env`, replacing `YOUR_API_KEY_HERE` with the key you copied.

    ```env
    # Get this key from your OpenProject user profile:
    # Account Settings -> Access Tokens -> Generate
    OPENPROJECT_API_KEY="YOUR_API_KEY_HERE"

    # Internal Docker network URL for the OpenProject instance. Do not change.
    OPENPROJECT_URL=http://openproject-proxy:80
    ```

### 3. Running the Full Stack

With the configuration in place, you can now launch all the services.

```bash
docker-compose up --build -d
```

You can check the status of the containers with `docker-compose ps` and view the logs of any service, for example, the MCP server:
```bash
docker-compose logs -f openproject-mcp
```

## Components

### OpenProject MCP Server (`openproject-mcp`)

This service acts as the bridge between the OpenProject API and the AI agents.

*   **Technology**: It is built using **Python** and the **FastMCP** library.
*   **Functionality**: It automatically loads the OpenAPI specification from the running OpenProject instance, converts all API endpoints into MCP-compliant tools, and exposes them over a `streamable-http` transport.
*   **OpenAPI Patching**: The official OpenProject OpenAPI spec has some structural inconsistencies and does not declare all optional fields as nullable. The `openapi_loader.py` script applies patches on-the-fly to fix these issues, ensuring the spec is valid and preventing validation errors at runtime.

#### Testing the MCP Server

An end-to-end test script is included to verify that the MCP server is running correctly and is properly integrated with the OpenProject API.

1.  **Install Test Dependencies**:
    ```bash
    pip install -r openproject-mcp/tests/requirements.txt
    ```

2.  **Run the Test**:
    ```bash
    python openproject-mcp/tests/test_mcp_server.py
    ```
    This script will:
    *   Connect to the MCP server at `http://localhost:8000/mcp`.
    *   List all available tools to confirm the server is operational.
    *   Execute the `view_work_package` tool for a specific Work Package ID to validate the full end-to-end connection.

### Analysis Agent (`analysis-agent`)

*(To be implemented)*

This component is intended to house an agent responsible for analyzing data retrieved from OpenProject.

### Codegen Agent (`codegen-agent`)

*(To be implemented)*

This component is intended to house an agent responsible for code generation tasks based on requirements from OpenProject.

## Project Structure

```
.
├── README.md
├── analysis-agent
│   ├── Dockerfile
│   ├── config.py
│   ├── main.py
│   └── requirements.txt
├── codegen-agent
│   ├── Dockerfile
│   ├── config.py
│   ├── main.py
│   └── requirements.txt
├── docker-compose.yml
└── openproject-mcp
    ├── Dockerfile
    ├── config.py
    ├── openapi_loader.py
    ├── proxy
    │   └── nginx.conf
    ├── requirements.txt
    ├── server.py
    └── tests
        ├── requirements.txt
        └── test_mcp_server.py
```