import os
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import Json

if os.path.exists(".env.local"):
    load_dotenv(".env.local")
try:
    from jira_utils import jira_get_recent_projects, jira_get_recent_user_activity, JiraError
except ImportError:
    jira_get_recent_projects = None
    jira_get_recent_user_activity = None

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
    Fetches the 20 most recent active projects and user's recent activity.
    """
    if jira_get_recent_projects is None or jira_get_recent_user_activity is None:
        return "Jira tools not available."
    
    context_parts = []
    
    # 1. Recent Projects
    projects_result = jira_get_recent_projects()
    if isinstance(projects_result, list) and projects_result and isinstance(projects_result[0], JiraError):
        context_parts.append(f"Error fetching Jira projects: {projects_result[0].error}")
    elif projects_result:
        projects_str = ["Recent Jira Projects:"]
        for project in projects_result:
            name = project.name
            key = project.key
            insight = project.insight
            total_issues = insight.get("totalIssueCount", "N/A") if insight else "N/A"
            last_update = insight.get("lastIssueUpdateTime", "N/A") if insight else "N/A"
            projects_str.append(f"- [{key}] {name} (Total Issues: {total_issues}, Last Update: {last_update})")
        context_parts.append("\n".join(projects_str))
    else:
        context_parts.append("No recent Jira projects found.")
        
    context_parts.append("\n" + "-"*20 + "\n")

    # 2. Recent User Activity
    activity_result = jira_get_recent_user_activity()
    if isinstance(activity_result, list) and activity_result and isinstance(activity_result[0], JiraError):
        context_parts.append(f"Error fetching recent activity: {activity_result[0].error}")
    elif activity_result:
        activity_str = ["Recent User Activity (Last 14 days):"]
        for issue in activity_result:
            key = issue.key
            summary = issue.fields.summary if issue.fields else "No Summary"
            status = issue.fields.status.name if issue.fields and issue.fields.status else "Unknown"
            activity_str.append(f"- [{key}] {summary} (Status: {status})")
        context_parts.append("\n".join(activity_str))
    else:
        context_parts.append("No recent user activity found.")

    return "\n".join(context_parts)

def route_prompt_rag():
    """TODO"""
    return

def text_to_jql():
    """TODO"""
    return