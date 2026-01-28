import os
from typing import Optional
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rlm import RLM
from rlm.core.types import RLMChatCompletion
from rlm.logger import RLMLogger
from rag_processing import translate_query

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
MODEL_NAME = os.getenv("RLM_MODEL_NAME", "gpt-4o")
API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY and BACKEND == "openai":
    print("Warning: OPENAI_API_KEY not found in environment.")

# Load Jira setup code
jira_setup_code = ""
if os.path.exists("jira_utils.py"):
    with open("jira_utils.py") as f:
        jira_setup_code = f.read()

rlm = None
try:
    rlm = RLM(
        backend=BACKEND,
        backend_kwargs={
            "model_name": MODEL_NAME,
            "api_key": API_KEY,
        },
        environment="local",
        environment_kwargs={
            "setup_code": jira_setup_code
        },
        max_depth=1,
        logger=logger,
        verbose=True,
    )
except Exception as e:
    print(f"Failed to initialize RLM: {e}")

class GenerateRequest(BaseModel):
    prompt: str
    context: Optional[str] = None

class GenerateResponse(BaseModel):
    result: str

@app.get("/")
def read_root():
    return {"status": "ok", "service": "RLM API"}

@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    if not rlm:
        raise HTTPException(status_code=500, detail="RLM backend not initialized")
    
    try:
        # Fetch Jira context
        jira_context = get_jira_context()
        
        # Construct full prompt
        context_str = request.context if request.context is not None else ""
        full_prompt = context_str + f"\n\n{jira_context}"
        root_prompt = translate_query(request.prompt)
        if root_prompt is None:
            root_prompt = request.prompt

        # Pass JIRA_TOOLS to completion
        result = rlm.completion(full_prompt, root_prompt, tools=JIRA_TOOLS)
        
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

def start():
    """Launched with `poetry run start` at root level"""
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    start()