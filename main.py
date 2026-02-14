import os
import sys
import traceback
from typing import Optional
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
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
if os.path.exists(".env.local"):
    load_dotenv(".env.local")
else:
    load_dotenv()

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
logger = RLMLogger(log_dir="./logs")

API_KEY = os.getenv("OPENAI_API_KEY")

class GenerateRequest(BaseModel):
    prompt: str
    context: Optional[str] = None
    model: str

class GeneralCompletionRequest(BaseModel):
    root_prompt: str
    prompt: str
    model: str

class GenerateResponse(BaseModel):
    result: str

@app.get("/")
def read_root():
    return {"status": "ok", "service": "RLM API"}

def parse_model_string(model_str: str) -> tuple[str, str]:
    if model_str.startswith("openai/"):
        return "openai", model_str.replace("openai/", "", 1)
    elif model_str.startswith("anthropic/"):
        return "anthropic", model_str.replace("anthropic/", "", 1)
    elif model_str.startswith("gemini/"):
        return "gemini", model_str.replace("gemini/", "", 1)
    elif model_str.startswith("azure/"):
        return "azure_openai", model_str.replace("azure/", "", 1)
    
    # Fallback/Legacy guessing
    if model_str.startswith("gpt"):
        return "openai", model_str
    elif model_str.startswith("claude"):
        return "anthropic", model_str
    elif model_str.startswith("gemini"):
        return "gemini", model_str
    elif model_str.startswith("azure"):
        return "azure_openai", model_str
    
    return "openai", model_str

@app.post("/general_completion", response_model=GenerateResponse)
async def general_completion(request: GeneralCompletionRequest):
    backend, model_name = parse_model_string(request.model)
    
    try:
        rlm = RLM(
            backend=backend,
            backend_kwargs={
                "model_name": model_name,
                "api_key": API_KEY,
            },
            environment="modal",
            environment_kwargs={
                "local_python_sources": "jira_app",
            },
            max_depth=1,
            logger=None,
            verbose=True,
        )
        
        # Call completion without tools and without extra context logic
        result = rlm.completion(request.prompt, request.root_prompt, tools=[])
        
        response_text = ""
        if isinstance(result, RLMChatCompletion):
            response_text = result.response
        elif isinstance(result, str):
            response_text = result
        else:
            response_text = str(result)
            
        return GenerateResponse(result=response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        
        # Initialize VerbosePrinter manually for the stream
        printer = VerbosePrinter(console=console, enabled=True)
        
        # Initialize VerbosePrinter for the server console (stdout)
        server_console = Console()
        server_printer = VerbosePrinter(console=server_console, enabled=True)
        
        # Print Metadata (Header) - Buffered for stream, direct for server
        metadata = RLMMetadata(
            root_model=model_name,
            max_depth=max_depth,
            max_iterations=30, # Default in RLM
            backend=backend,
            backend_kwargs=filter_sensitive_keys(backend_kwargs),
            environment_type="modal",
            environment_kwargs=filter_sensitive_keys(environment_kwargs),
            other_backends=None
        )
        with console.capture() as capture:
            printer.print_metadata(metadata)
        console.file.write(capture.get())
        server_printer.print_metadata(metadata)

        rlm = RLM(
            backend=backend,
            backend_kwargs=backend_kwargs,
            environment="modal",
            environment_kwargs=environment_kwargs,
            max_depth=max_depth,
            logger=None,
            verbose=False, # Disable internal verbose printing
            verbose_console=console
        )

        # Construct full prompt
        context_str = body.context if body.context is not None else ""
        full_prompt = context_str + f"\n\n{jira_context}"
        root_prompt = translate_query(body.prompt)
        if root_prompt is None:
            root_prompt = body.prompt

        iteration_count = 0
        def on_iteration(iteration: RLMIteration):
            nonlocal iteration_count
            iteration_count += 1
            
            # Print Iteration - Buffered for stream
            with console.capture() as capture:
                printer.print_iteration(iteration, iteration_count)
            console.file.write(capture.get())
            
            # Print Iteration - Direct for server
            server_printer.print_iteration(iteration, iteration_count)

        # Pass JIRA_TOOLS. Setup code is already handled in init.
        result = rlm.completion(
            full_prompt, 
            root_prompt, 
            tools=JIRA_TOOLS,
            iteration_callback=on_iteration
        )
        
        # Print Final Answer and Summary - Buffered for stream, direct for server
        with console.capture() as capture:
            if isinstance(result, RLMChatCompletion):
                printer.print_final_answer(result.response)
                printer.print_summary(iteration_count, result.execution_time, result.usage_summary.to_dict())
            else:
                printer.print_final_answer(result)
        console.file.write(capture.get())
        
        if isinstance(result, RLMChatCompletion):
            server_printer.print_final_answer(result.response)
            server_printer.print_summary(iteration_count, result.execution_time, result.usage_summary.to_dict())
        else:
            server_printer.print_final_answer(result)

    except Exception as e:
        console.print(f"[bold red]Error in RLM execution:[/bold red] {e}")
        traceback.print_exc()

@app.post("/generate")
async def generate(request: Request, body: GenerateRequest):
    jira_token = request.headers.get("X-Jira-Token")
    jira_cloud_id = request.headers.get("X-Jira-Resource-Id")
    jira_base_url = f"https://api.atlassian.com/ex/jira/{jira_cloud_id}"
    jira_context = get_jira_context(jira_base_url, jira_token)

    if not jira_token or not jira_cloud_id or not jira_context:
        raise HTTPException(status_code=401, detail="Missing Jira credentials (X-Jira-Token, X-Jira-Resource-Id)")

    try:

        # Fetch Jira context
        
        # Construct dynamic setup code with wrappers
        # We import from jira_app.jira_utils (available in image) and wrap to inject credentials
        setup_code = f"""
from jira_app.jira_utils import *
from jira_app.jira_utils import (
    jira_search_issues as _raw_jira_search_issues,
    jira_get_issue as _raw_jira_get_issue,
    jira_get_issue_comments as _raw_jira_get_issue_comments,
    jira_get_project as _raw_jira_get_project,
    jira_list_projects as _raw_jira_list_projects
)

def jira_search_issues(jql, fields="summary,status,assignee,priority,created,description,issuetype,issuelinks,comment,project, duedate"):
    return _raw_jira_search_issues(jql, "{jira_base_url}", "{jira_token}", fields)

def jira_get_issue(issue_key):
    return _raw_jira_get_issue(issue_key, "{jira_base_url}", "{jira_token}")

def jira_get_issue_comments(issue_key):
    return _raw_jira_get_issue_comments(issue_key, "{jira_base_url}", "{jira_token}")

def jira_get_project(project_key):
    return _raw_jira_get_project(project_key, "{jira_base_url}", "{jira_token}")

def jira_list_projects():
    return _raw_jira_list_projects("{jira_base_url}", "{jira_token}")
"""
        
        # Initialize ThreadedStreamer with the target function
        # We pass arguments via kwargs later or here
        streamer = ThreadedStreamer(target=run_rlm_generation)
        
        # Create console that writes to the streamer's capturer
        # Force terminal=False (default) to strip colors, or True to keep them?
        # User asked for "what I see in my terminal", which implies colors. 
        # But for web usage, plain text is safer unless frontend handles ANSI.
        # We'll stick to default (likely plain text) or set force_terminal=False explicit.
        # However, rich.Console(file=...) usually defaults force_terminal=False.
        console = Console(file=streamer.capturer, width=100, force_terminal=False)
        
        # Set the arguments for the target function
        streamer.kwargs = {
            "console": console,
            "body": body,
            "jira_context": jira_context,
            "setup_code": setup_code,
            "jira_base_url": jira_base_url,
            "jira_token": jira_token
        }
        
        return StreamingResponse(streamer.stream_generator(), media_type="text/plain")

    except Exception:
        return {"status": "500", "detail": "internal server error"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)