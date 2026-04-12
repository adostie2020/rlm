import sys
import os
from pathlib import Path

# Force UTF-8 for stdout/stderr on Windows to avoid cp1252 errors with Rich
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        # Python < 3.7 or other issues
        pass

# Add root directory to sys.path to allow importing rlm, jira_app, etc.
# We are in next-fastapi-app/api/index.py, so root is ../../
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))


import traceback
from typing import Optional, List
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from rich.console import Console

from rlm import RLM
from rlm.core.types import RLMChatCompletion, RLMIteration, RLMMetadata
from rlm.logger import RLMLogger, VerbosePrinter
from rlm.utils.stream_capturer import ThreadedStreamer
from rlm.utils.rlm_utils import filter_sensitive_keys

# Import tools
try:
    from tools import JIRA_TOOLS
except ImportError:
    JIRA_TOOLS = []
    print("Warning: Could not import JIRA_TOOLS from tools.py")

# Load environment variables
# Load root .env first
if os.path.exists(str(root_path / ".env.local")):
    load_dotenv(str(root_path / ".env.local"))
elif os.path.exists(str(root_path / ".env")):
    load_dotenv(str(root_path / ".env"))

# Load next-fastapi-app specific env (override)
if os.path.exists(".env.local"):
    load_dotenv(".env.local", override=True)

from rag_processing import translate_query, get_jira_context

app = FastAPI(title="RLM API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RLM
logger = RLMLogger(log_dir=str(root_path / "logs"))

API_KEY = os.getenv("OPENAI_API_KEY")

class GenerateRequest(BaseModel):
    prompt: str
    context: Optional[str] = None
    model: str

class GenerateResponse(BaseModel):
    result: str

def parse_model_string(model_str: str) -> tuple[str, str]:
    if model_str.startswith("openai/"):
        return "openai", model_str.replace("openai/", "", 1)
    elif model_str.startswith("anthropic/"):
        return "anthropic", model_str.replace("anthropic/", "", 1)
    elif model_str.startswith("gemini/"):
        return "gemini", model_str.replace("gemini/", "", 1)
    elif model_str.startswith("azure/"):
        return "azure_openai", model_str.replace("azure/", "", 1)
    
    if model_str.startswith("gpt"):
        return "openai", model_str
    elif model_str.startswith("claude"):
        return "anthropic", model_str
    elif model_str.startswith("gemini"):
        return "gemini", model_str
    elif model_str.startswith("azure"):
        return "azure_openai", model_str
    
    return "openai", model_str

def run_rlm_generation(console: Console, body: GenerateRequest, jira_context: str, setup_code: str, jira_base_url: str, jira_token: str):
    """
    Function to run RLM generation in a separate thread.
    Output is captured via the passed console.
    """
    try:
        backend, model_name = parse_model_string(body.model)
        backend_kwargs = {
            "model_name": model_name,
            "api_key": API_KEY,
        }
        environment_kwargs = {
            "setup_code": setup_code,
            "local_python_sources": "jira_app",
        }
        max_depth = 1
        
        printer = VerbosePrinter(console=console, enabled=True)
        server_console = Console()
        server_printer = VerbosePrinter(console=server_console, enabled=True)
        
        metadata = RLMMetadata(
            root_model=model_name,
            max_depth=max_depth,
            max_iterations=30,
            backend=backend,
            backend_kwargs=filter_sensitive_keys(backend_kwargs),
            environment_type="modal",
            environment_kwargs=filter_sensitive_keys(environment_kwargs),
            other_backends=None
        )
        printer.print_metadata(metadata)
        server_printer.print_metadata(metadata)

        rlm = RLM(
            backend=backend,
            backend_kwargs=backend_kwargs,
            environment="modal",
            environment_kwargs=environment_kwargs,
            max_depth=max_depth,
            logger=None,
            verbose=False,
            verbose_console=console
        )

        context_str = body.context if body.context is not None else ""
        full_prompt = context_str + f"\n\n{jira_context}"
        print(f"[DEBUG] Jira Context Length: {len(jira_context)}")
        print(f"[DEBUG] Full Prompt (first 500 chars): {full_prompt[:500]}...")
        
        root_prompt = translate_query(body.prompt)
        if root_prompt is None:
            root_prompt = body.prompt

        iteration_count = 0
        def on_iteration(iteration: RLMIteration):
            nonlocal iteration_count
            iteration_count += 1
            
            printer.print_iteration(iteration, iteration_count)
            server_printer.print_iteration(iteration, iteration_count)
            server_printer.print_iteration(iteration, iteration_count)

        result = rlm.completion(
            full_prompt, 
            root_prompt, 
            tools=JIRA_TOOLS,
            iteration_callback=on_iteration
        )
        
        if isinstance(result, RLMChatCompletion):
            printer.print_final_answer(result.response)
            printer.print_summary(iteration_count, result.execution_time, result.usage_summary.to_dict())
        else:
            printer.print_final_answer(result)
        
        if isinstance(result, RLMChatCompletion):
            server_printer.print_final_answer(result.response)
            server_printer.print_summary(iteration_count, result.execution_time, result.usage_summary.to_dict())
        else:
            server_printer.print_final_answer(result)

    except Exception as e:
        console.print(f"[bold red]Error in RLM execution:[/bold red] {e}")
        traceback.print_exc()

# New adaptors for Next.js
class ClientAttachment(BaseModel):
    name: str
    contentType: str
    url: str

class ToolInvocation(BaseModel):
    toolCallId: str
    toolName: str
    args: dict
    result: dict

class MessagePart(BaseModel):
    type: str
    text: Optional[str] = None

class ClientMessage(BaseModel):
    id: Optional[str] = None
    role: str
    content: Optional[str] = ""
    parts: Optional[List[MessagePart]] = None
    experimental_attachments: Optional[List[ClientAttachment]] = None
    toolInvocations: Optional[List[ToolInvocation]] = None

class ChatRequest(BaseModel):
    messages: List[ClientMessage]

@app.post("/api/chat")
async def handle_chat_data(request: Request, body: ChatRequest, protocol: str = Query('data')):
    # Extract prompt from last user message
    if not body.messages:
        raise HTTPException(status_code=400, detail="No messages provided")
    
    last_message = body.messages[-1]
    
    # Extract content from parts if content is empty (AI SDK 4+ style)
    prompt = last_message.content
    if not prompt and last_message.parts:
        prompt = " ".join([p.text for p in last_message.parts if p.type == "text" and p.text])
    
    if not prompt:
        prompt = ""
    
    # Defaults
    model = "openai/gpt-4o"
    
    # Jira Auth
    jira_token = request.headers.get("X-Jira-Token")
    jira_cloud_id = request.headers.get("X-Jira-Resource-Id")
    
    jira_base_url = f"https://api.atlassian.com/ex/jira/{jira_cloud_id}" if jira_cloud_id else ""
    jira_context = "No Jira credentials provided."

    if jira_token and jira_base_url:
        try:
            # We assume get_jira_context can handle auth errors or returns None/Error string
            jira_context = get_jira_context(jira_base_url, jira_token) or "Jira context not available."
        except Exception as e:
            print(f"Error fetching Jira context: {e}")
            jira_context = "Error fetching Jira context."

    setup_code = f"""
from jira_app.jira_utils import *
from jira_app.jira_utils import (
    jira_search_issues as _raw_jira_search_issues,
    jira_get_issue as _raw_jira_get_issue,
    jira_get_issue_comments as _raw_jira_get_issue_comments,
    jira_get_project as _raw_jira_get_project,
    jira_list_projects as _raw_jira_list_projects
)

def jira_search_issues(jql: str, start_at: int = 0, max_results: int = 20, fields: str = "summary,status,assignee,priority,created,description,issuetype,issuelinks,comment,project, duedate"):
    if isinstance(jql, dict):
        jql = jql.get('jql', '')
    return _raw_jira_search_issues(jql, "{jira_base_url}", "{jira_token}", start_at, max_results, fields)

def jira_get_issue(issue_key: str):
    if isinstance(issue_key, dict):
        issue_key = issue_key.get('issue_key', '')
    return _raw_jira_get_issue(issue_key, "{jira_base_url}", "{jira_token}")

def jira_get_issue_comments(issue_key: str):
    if isinstance(issue_key, dict):
        issue_key = issue_key.get('issue_key', '')
    return _raw_jira_get_issue_comments(issue_key, "{jira_base_url}", "{jira_token}")

def jira_get_project(project_key: str):
    if isinstance(project_key, dict):
        project_key = project_key.get('project_key', '')
    return _raw_jira_get_project(project_key, "{jira_base_url}", "{jira_token}")

def jira_list_projects():
    return _raw_jira_list_projects("{jira_base_url}", "{jira_token}")
"""

    gen_request = GenerateRequest(prompt=prompt, context=None, model=model)

    streamer = ThreadedStreamer(target=run_rlm_generation, protocol=protocol)
    # Force terminal=False to strip colors for clean stream, OR True if frontend expects ANSI
    # The user said "what I see in my terminal", so maybe True?
    # But usually frontend components won't parse ANSI unless specifically designed (like xterm.js).
    # The default Next.js example doesn't seem to have ANSI parser.
    # I'll default to False to be safe, but keep width large.
    console = Console(file=streamer.capturer, width=100, force_terminal=False)
    
    streamer.kwargs = {
        "console": console,
        "body": gen_request,
        "jira_context": jira_context,
        "setup_code": setup_code,
        "jira_base_url": jira_base_url,
        "jira_token": jira_token or ""
    }
    
    response = StreamingResponse(
        streamer.stream_generator(), 
        media_type="text/event-stream" if protocol == "vercel_data_stream" else "text/plain"
    )
    response.headers['x-vercel-ai-data-stream'] = 'v1'
    response.headers['Cache-Control'] = 'no-cache, no-transform'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Connection'] = 'keep-alive'
    return response

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
