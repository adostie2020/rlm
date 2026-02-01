import re
from typing import Any

# Mock LocalREPL
class MockEnv:
    def __init__(self):
        self.locals = {"final_answer": "42", "my_var": "Hello World"}
        self.globals = {"FINAL_VAR": self._final_var}

    def _final_var(self, variable_name: str) -> str:
        variable_name = variable_name.strip().strip("'\"")
        if variable_name in self.locals:
            return str(self.locals[variable_name])
        return f"Error: Variable '{variable_name}' not found"

    def execute_code(self, code: str):
        # Extremely simple mock execution for print(FINAL_VAR(...))
        # Expected code format: print(FINAL_VAR('var_name'))
        
        # Extract content inside print(...)
        match = re.match(r"print\((.*)\)", code)
        if match:
            inner = match.group(1)
            # Evaluate inner expression using globals/locals
            # We can't easily allow arbitrary exec here without safety, but for this specific pattern:
            if inner.startswith("FINAL_VAR("):
                # Extract arg to FINAL_VAR
                arg_match = re.match(r"FINAL_VAR\((.*)\)", inner)
                if arg_match:
                    arg = eval(arg_match.group(1)) # Safe-ish for 'string' in this test
                    result = self._final_var(arg)
                    return type('Result', (), {'stdout': result, 'stderr': ''})()
        
        return type('Result', (), {'stdout': '', 'stderr': 'Execution failed'})()

def find_final_answer(text: str, environment=None) -> str | None:
    # Check for FINAL_VAR pattern first - must be at start of line
    final_var_pattern = r"^\s*FINAL_VAR\((.*?)\)"
    match = re.search(final_var_pattern, text, re.MULTILINE | re.DOTALL)
    if match:
        variable_name = match.group(1).strip().strip("'\"")
        print(f"DEBUG: Found FINAL_VAR with variable_name='{variable_name}'")
        if environment is not None:
            # Replicating exact logic from rlm/utils/parsing.py
            code_to_exec = f"print(FINAL_VAR({variable_name!r}))"
            print(f"DEBUG: Executing code: {code_to_exec}")
            result = environment.execute_code(code_to_exec)
            final_answer = result.stdout.strip()
            if final_answer == "":
                final_answer = result.stderr.strip() or ""
            return final_answer
        return None

    # Check for FINAL pattern - must be at start of line
    final_pattern = r"^\s*FINAL\((.*?)\)"
    match = re.search(final_pattern, text, re.MULTILINE | re.DOTALL)
    if match:
        return match.group(1).strip()

    return None

env = MockEnv()

print("--- Test 1: FINAL_VAR(final_answer) ---")
text1 = "FINAL_VAR(final_answer)"
res1 = find_final_answer(text1, env)
print(f"Result 1: {res1!r}")

print("\n--- Test 2: FINAL(final_answer) ---")
text2 = "FINAL(final_answer)"
res2 = find_final_answer(text2, env)
print(f"Result 2: {res2!r}")
if res2 == "final_answer":
    print("CONFIRMED: FINAL(final_answer) returns literal string 'final_answer'")


print("\n--- Test 3: FINAL_VAR(\"final_answer\") ---")
text3 = "FINAL_VAR(\"final_answer\")"
res3 = find_final_answer(text3, env)
print(f"Result 3: {res3!r}")

print("\n--- Test 4: FINAL_VAR('final_answer') ---")
text4 = "FINAL_VAR('final_answer')"
res4 = find_final_answer(text4, env)
print(f"Result 4: {res4!r}")