import os
import sys
import traceback
from typing import Optional
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rlm import RLM
from rlm.core.types import RLMChatCompletion
from rlm.logger import RLMLogger

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

@app.post("/generate", response_model=GenerateResponse)
async def generate(request: Request, body: GenerateRequest):
    jira_token = request.headers.get("X-Jira-Token")
    jira_cloud_id = request.headers.get("X-Jira-Resource-Id")

    if not jira_token or not jira_cloud_id:
        raise HTTPException(status_code=401, detail="Missing Jira credentials (X-Jira-Token, X-Jira-Resource-Id)")

    try:
        jira_base_url = f"https://api.atlassian.com/ex/jira/{jira_cloud_id}"

        # Fetch Jira context
        jira_context = get_jira_context(jira_base_url, jira_token)
        
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
        backend, model_name = parse_model_string(body.model)
        rlm = RLM(
            backend=backend,
            backend_kwargs={
                "model_name": model_name,
                "api_key": API_KEY,
            },
            environment="modal",
            environment_kwargs={
                "setup_code": setup_code,
                "local_python_sources": "jira_app",
            },
            max_depth=1,
            logger=None,
            verbose=True,
        )

        # Construct full prompt
        context_str = body.context if body.context is not None else ""
        full_prompt = context_str + f"\n\n{jira_context}"
        root_prompt = translate_query(body.prompt)
        if root_prompt is None:
            root_prompt = body.prompt

        # Pass JIRA_TOOLS. Setup code is already handled in init.
        result = rlm.completion(
            full_prompt, 
            root_prompt, 
            tools=JIRA_TOOLS
        )
        
        response_text = ""
        if isinstance(result, RLMChatCompletion):
            response_text = result.response
        elif isinstance(result, str):
            response_text = result
        else:
            response_text = str(result)
            
        return GenerateResponse(result=response_text)
    except Exception as e:
        print(f"Error in /generate endpoint: {e}", file=sys.stderr)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)