import os
from typing import Optional
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rlm import RLM
from rlm.core.types import RLMChatCompletion
from rlm.logger import RLMLogger
from rag_processing import translate_query
from jira_utils import _get_jira_session

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

# Configuration
BACKEND = os.getenv("RLM_BACKEND", "openai")
API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY and BACKEND == "openai":
    print("Warning: OPENAI_API_KEY not found in environment.")

# Load Jira setup code base
jira_setup_base = ""
if os.path.exists("jira_utils.py"):
    with open("jira_utils.py") as f:
        jira_setup_base = f.read()
def rlm_init(model_name):
    rlm = None
    try:
        rlm = RLM(
            backend=BACKEND,
            backend_kwargs={
                "model_name": model_name,
                "api_key": API_KEY,
            },
            environment="modal",
            environment_kwargs={
                "setup_code": jira_setup_base # Default setup
            },
            max_depth=1,
            logger=logger,
            verbose=True,
        )
    except Exception as e:
        print(f"Failed to initialize RLM: {e}")
    return rlm

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

@app.post("/general_completion", response_model=GenerateResponse)
async def general_completion(request: GeneralCompletionRequest):
    rlm = rlm_init(request.model)
    if not rlm:
        raise HTTPException(status_code=500, detail="RLM backend not initialized")
    
    try:
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
    rlm = rlm_init(body.model)

    if not rlm:
        raise HTTPException(status_code=500, detail="RLM backend not initialized")
    
    try:
        # Extract Jira credentials from headers
        jira_token = request.headers.get("X-Jira-Token")
        jira_cloud_id = request.headers.get("X-Jira-Resource-Id")
        
        jira_base_url = None
        if jira_cloud_id:
            jira_base_url = f"https://api.atlassian.com/ex/jira/{jira_cloud_id}"

        # Fetch Jira context
        jira_context = ""
        if jira_base_url and jira_token:
            jira_context = get_jira_context(jira_base_url, jira_token)
        else:
            jira_context = "Jira credentials not provided in headers (X-Jira-Token, X-Jira-Resource-Id)."
        
        # Construct dynamic setup code with wrappers
        # We wrap the functions to inject the token/url so the LLM doesn't need to know them
        if jira_base_url and jira_token:
            wrappers = f"""
# --- Jira Wrapper Functions Injected by Main ---
_raw_jira_search_issues = jira_search_issues
def jira_search_issues(jql, fields="summary,status,assignee,priority,created,description,issuetype,issuelinks,comment,project, duedate"):
    return _raw_jira_search_issues(jql, "{jira_base_url}", "{jira_token}", fields)

_raw_jira_get_issue = jira_get_issue
def jira_get_issue(issue_key):
    return _raw_jira_get_issue(issue_key, "{jira_base_url}", "{jira_token}")

_raw_jira_get_issue_comments = jira_get_issue_comments
def jira_get_issue_comments(issue_key):
    return _raw_jira_get_issue_comments(issue_key, "{jira_base_url}", "{jira_token}")

_raw_jira_get_project = jira_get_project
def jira_get_project(project_key):
    return _raw_jira_get_project(project_key, "{jira_base_url}", "{jira_token}")

_raw_jira_list_projects = jira_list_projects
def jira_list_projects():
    return _raw_jira_list_projects("{jira_base_url}", "{jira_token}")
"""
            dynamic_setup_code = jira_setup_base + wrappers
        else:
            dynamic_setup_code = jira_setup_base

        # Construct full prompt
        context_str = body.context if body.context is not None else ""
        full_prompt = context_str + f"\n\n{jira_context}"
        root_prompt = translate_query(body.prompt)
        if root_prompt is None:
            root_prompt = body.prompt

        # Pass JIRA_TOOLS and dynamic setup code to completion
        # Use environment_overrides to pass the request-specific setup code
        result = rlm.completion(
            full_prompt, 
            root_prompt, 
            tools=JIRA_TOOLS,
            environment_overrides={"setup_code": dynamic_setup_code}
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
        raise HTTPException(status_code=500, detail=str(e))