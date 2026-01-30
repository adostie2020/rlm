import os
from dotenv import load_dotenv
import rlm.clients.openai

# 1. Check raw env before explicit load (dotenv might auto-load)
print(f"Raw os.getenv('OPENAI_API_KEY'): {os.getenv('OPENAI_API_KEY') is not None}")

# 2. Explicit load
loaded = load_dotenv()
print(f"load_dotenv() returned: {loaded}")
print(f"Post-load os.getenv('OPENAI_API_KEY'): {os.getenv('OPENAI_API_KEY') is not None}")

# 3. Check what the module saw at import time
print(f"rlm.clients.openai.DEFAULT_OPENAI_API_KEY: {rlm.clients.openai.DEFAULT_OPENAI_API_KEY is not None}")

# 4. Check current working directory to ensure we are where we think we are
print(f"CWD: {os.getcwd()}")
print(f"Files in CWD: {os.listdir('.')}")
