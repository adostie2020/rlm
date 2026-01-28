import os
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import Json

if os.path.exists(".env.local"):
    load_dotenv(".env.local")
try:
    from jira_utils import jira_get_recent_projects, JiraError
except ImportError:
    jira_get_recent_projects = None

client = OpenAI()

def translate_query(query: str) -> Json:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
        {"role": "system", "content": """ROLE: You are a specialized prompt engineer for a recursive language model (i.e. a language model which is able to call other prompts to explore context). 
        GOAL: Translate a user query into a concise, high-level prompt for a recursive language model.
        HINT: Include in your prompt that the rlm has access to tools. If it is not given relevant details about the jira project in context, it can call a jira endpoint for additional details."""},
        {"role": "user", "content": query }]
    )
    print(response)
    return response.choices[0].message.content

def get_jira_context() -> str:
    """
    Fetches the 20 most recent active projects for the user with insight details.
    """
    if jira_get_recent_projects is None:
        return "Jira tools not available."
    
    result = jira_get_recent_projects()
    
    if isinstance(result, list) and result and isinstance(result[0], JiraError):
        return f"Error fetching Jira projects: {result[0].error}"
    
    if not result:
        return "No recent Jira projects found."
    
    # Format projects
    projects_str = []
    for project in result:
        name = project.name
        key = project.key
        insight = project.insight
        total_issues = insight.get("totalIssueCount", "N/A") if insight else "N/A"
        last_update = insight.get("lastIssueUpdateTime", "N/A") if insight else "N/A"
        projects_str.append(f"- [{key}] {name} (Total Issues: {total_issues}, Last Update: {last_update})")
        
    return "Recent Jira Projects:\n" + "\n".join(projects_str)

def route_prompt_rag():
    """TODO"""
    return

def text_to_jql():
    """TODO"""
    return