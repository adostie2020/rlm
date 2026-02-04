import os
import sys
from main import rlm_init, JIRA_TOOLS

# Mock OPENAI_API_KEY if not present (though main.py loads .env)
# We assume .env exists and has the key, or the environment has it.
# If not, this might fail with Auth error, but we are looking for "invalid model ID".

try:
    print("Initializing RLM with model='gpt-4o'")
    rlm = rlm_init("gpt-4o")
    if not rlm:
        print("RLM init failed")
        sys.exit(1)

    print("Calling completion...")
    # mocking tools as empty or JIRA_TOOLS
    result = rlm.completion("Hello", tools=JIRA_TOOLS)
    print("Result:", result)

except Exception as e:
    print(f"Caught exception: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
