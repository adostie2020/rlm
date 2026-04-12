import os
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import Json

if os.path.exists(".env.local"):
    load_dotenv(".env.local")
try:
    from jira_app.jira_utils import jira_get_recent_projects, jira_get_recent_user_activity, jira_get_open_user_issues, JiraError
except ImportError:
    jira_get_recent_projects = None
    jira_get_recent_user_activity = None
    jira_get_open_user_issues = None

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
    return response.choices[0].message.content + "When you have completed processing, output a final answer."

def get_jira_context(jira_base_url: str, jira_token: str, next_page_token: str | None = None) -> str | None:
    """
    Fetches the 20 most recent active projects, user's recent activity, and open issues.
    Supports pagination for open issues via `next_page_token`.
    Returns None if any of the Jira API calls fail.
    """
    if jira_get_recent_projects is None or jira_get_recent_user_activity is None or jira_get_open_user_issues is None:
        return "Jira tools not available."
    
    start_at = int(next_page_token) if next_page_token else 0
    max_results = 20
    context_parts = []
    
    # 1. Recent Projects
    # Only fetch projects if we are on the first page to reduce noise, or always fetch?
    # Usually context is rebuilt, so we probably want projects always, or maybe just on page 0.
    # Let's keep it simple and always fetch for now, unless requested otherwise.
    # Actually, if I am paging through issues, I might not need projects again.
    # But let's stick to the previous behavior + pagination for issues.
    
    projects_result = jira_get_recent_projects(jira_base_url, jira_token)
    if isinstance(projects_result, list) and projects_result and isinstance(projects_result[0], JiraError):
        return None
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
    activity_result = jira_get_recent_user_activity(jira_base_url, jira_token)
    
    # Handle both list (legacy) and dict (new) returns
    activity_issues = []
    if isinstance(activity_result, dict):
        activity_issues = activity_result.get("jira_issues", [])
    elif isinstance(activity_result, list):
        activity_issues = activity_result

    print(f"[RAG] Fetched {len(activity_issues)} activity items")
    
    if isinstance(activity_result, list) and activity_result and isinstance(activity_result[0], JiraError):
        print(f"[RAG] Jira Error in activity: {activity_result[0]}")
        return None
    elif activity_issues:
        activity_str = ["Recent User Activity (Last 14 days):"]
        for issue in activity_issues:
            key = issue.key
            summary = issue.fields.summary if issue.fields else "No Summary"
            status = issue.fields.status.name if issue.fields and issue.fields.status else "Unknown"
            activity_str.append(f"- [{key}] {summary} (Status: {status})")
        context_parts.append("\n".join(activity_str))
    else:
        context_parts.append("No recent user activity found.")

    context_parts.append("\n" + "-"*20 + "\n")

    # 3. Open Issues (Assigned/Reported)
    open_issues_result = jira_get_open_user_issues(jira_base_url, jira_token, start_at=start_at, max_results=max_results)
    
    # Handle both list (legacy) and dict (new) returns
    open_issues = []
    if isinstance(open_issues_result, dict):
        open_issues = open_issues_result.get("jira_issues", [])
    elif isinstance(open_issues_result, list):
        open_issues = open_issues_result

    print(f"[RAG] Fetched {len(open_issues)} open issues")
    
    if isinstance(open_issues_result, list) and open_issues_result and isinstance(open_issues_result[0], JiraError):
        print(f"[RAG] Jira Error in open issues: {open_issues_result[0]}")
        return None
    elif open_issues:
        open_issues_str = [f"Open Issues (Assigned/Reported) - Page starting at {start_at}:"]
        for issue in open_issues:
            key = issue.key
            summary = issue.fields.summary if issue.fields else "No Summary"
            status = issue.fields.status.name if issue.fields and issue.fields.status else "Unknown"
            priority = issue.fields.priority.name if issue.fields and issue.fields.priority else "Unknown"
            open_issues_str.append(f"- [{key}] {summary} (Status: {status}, Priority: {priority})")
        context_parts.append("\n".join(open_issues_str))
        
        # Add Next Page Token if we likely have more results
        if len(open_issues) == max_results:
             context_parts.append(f"\nNext Page Token: {start_at + max_results}")

    else:
        context_parts.append("No open issues found for user.")

    return "\n".join(context_parts)

def route_prompt_rag():
    """TODO"""
    return

def text_to_jql():
    """TODO"""
    return