import os
# Simulate the environment BEFORE load_dotenv
if "OPENAI_API_KEY" in os.environ:
    del os.environ["OPENAI_API_KEY"]

# Simulate the import chain
# This defines the module-level constant as None
import rlm.clients.openai 
print(f"Module default: {rlm.clients.openai.DEFAULT_OPENAI_API_KEY}")

from dotenv import load_dotenv
load_dotenv() # Load the .env file

key = os.getenv("OPENAI_API_KEY")
print(f"Key after load: {key is not None}")

# Simulate the call
kwargs = {"api_key": key}
client = rlm.clients.openai.OpenAIClient(**kwargs)
print("Client initialized successfully")
