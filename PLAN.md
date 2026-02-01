# RLM Production Deployment Plan

This plan details the steps to transition the RLM project to a production-ready state, utilizing **Render** for hosting the core API and **Modal** for the isolated execution environment ("production venv").

## Architecture

1.  **Core API (FastAPI) on Render**:
    *   The `main.py` FastAPI application serves as the central controller.
    *   It handles user requests, manages Jira authentication, and orchestrates the LLM interaction.
    *   **Deployment**: Docker container running on Render Web Service.
    *   **Env Vars**: `OPENAI_API_KEY`, `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`, `RLM_BACKEND`.

2.  **Execution Environment on Modal**:
    *   The `ModalREPL` (in `rlm/environments/modal_repl.py`) acts as the "production venv".
    *   It provisions an isolated sandbox with a predefined set of packages (`APT_PACKAGES`, `PIP_PACKAGES`).
    *   **Role**: Executes generated Python code safely.
    *   **Auth**: The Render app authenticates to Modal using a token.

3.  **Frontend (Visualizer) on Render (Optional)**:
    *   The Next.js app in `visualizer/` provides the UI.
    *   **Deployment**: Node.js Static/Web Service on Render.
    *   **Env Vars**: `NEXT_PUBLIC_API_URL` (pointing to the FastAPI service).

## Implementation Steps

### 1. Render Configuration (`render.yaml`)
Create a `render.yaml` file to automate the deployment of both the backend and frontend on Render using **Native Environments**.

**Backend (Python Service):**
*   **Environment**: Native Python (no Docker needed).
*   **Build Command**: `pip install uv && uv sync --frozen`
    *   Installs `uv` and restores dependencies from `uv.lock`.
*   **Start Command**: `uv run uvicorn main:app --host 0.0.0.0 --port $PORT`
*   **Env Vars**: `OPENAI_API_KEY`, `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`, `RLM_BACKEND`.

**Frontend (Static Site):**
*   **Environment**: Node.js
*   **Build Command**: `npm install && npm run build` (inside `visualizer/`)
*   **Publish Directory**: `visualizer/.next` or `visualizer/out` (depending on export).

### 2. Define Production Modal Image
Review `rlm/environments/modal_repl.py`.
*   Ensure the `get_default_image` function is robust.
*   (Optional) If we need to pin specific versions for "production" stability, we can define a `requirements.in` or similar for the sandbox specifically.

### 3. Integration Verification
*   Ensure `main.py` correctly passes the Modal auth token if needed.
*   Test the full flow: Frontend -> Backend -> Modal Sandbox.

## Required Environment Variables for Render
*   `OPENAI_API_KEY`: For the LLM backend.
*   `MODAL_TOKEN_ID`: For authenticating with Modal.
*   `MODAL_TOKEN_SECRET`: For authenticating with Modal.
*   `RLM_BACKEND`: e.g., "openai".
