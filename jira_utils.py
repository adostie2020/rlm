import os
import requests
from typing import Any
from pydantic import BaseModel, Field

# Environment variables expected:
# JIRA_BASE_URL
# JIRA_EMAIL
# JIRA_API_TOKEN

# --- Pydantic Models ---

class JiraUser(BaseModel):
    displayName: str | None = None
    emailAddress: str | None = None
    accountId: str | None = None

class JiraStatus(BaseModel):
    name: str | None = None
    statusCategory: dict[str, Any] | None = None

class JiraPriority(BaseModel):
    name: str | None = None
    id: str | None = None

class JiraIssueType(BaseModel):
    name: str | None = None
    subtask: bool | None = None

class JiraProject(BaseModel):
    id: str
    key: str
    name: str
    projectTypeKey: str | None = None
    insight: dict[str, Any] | None = None

class JiraFields(BaseModel):
    summary: str | None = None
    status: JiraStatus | None = None
    assignee: JiraUser | None = None
    priority: JiraPriority | None = None
    issuetype: JiraIssueType | None = None
    created: str | None = None
    description: Any | None = None  # ADF format in v3, complex dict
    project: JiraProject | None = None
    # Add other fields as needed, using Any for complex ones to prevent validation errors
    # on unexpected structures
    issuelinks: list[Any] | None = None
    comment: dict[str, Any] | None = None

class JiraIssue(BaseModel):
    id: str
    key: str
    self: str
    fields: JiraFields | None = None

class JiraComment(BaseModel):
    id: str | None = None
    author: JiraUser | None = None
    body: Any | None = None # ADF format
    created: str | None = None
    updated: str | None = None

class JiraError(BaseModel):
    error: str

# --- Helper ---

def _get_jira_session():
    base_url = os.environ.get("JIRA_BASE_URL")
    email = os.environ.get("JIRA_EMAIL")
    token = os.environ.get("JIRA_API_TOKEN")

    if not all([base_url, email, token]):
        raise ValueError("Missing Jira credentials. Please set JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN in the environment.")
    
    session = requests.Session()
    session.auth = (email, token)
    session.headers.update({
        "Accept": "application/json",
        "Content-Type": "application/json"
    })
    return session, base_url.rstrip("/")

# --- Tool Functions ---

def jira_search_issues(jql: str, max_results: int = 50) -> list[JiraIssue] | list[JiraError]:
    """Search for Jira issues using JQL and return validated Pydantic models."""
    try:
        session, base_url = _get_jira_session()
        url = f"{base_url}/rest/api/3/search/jql"
        params = {
            "jql": jql,
            "maxResults": max_results,
            "fields": "summary,status,assignee,priority,created,description,issuetype,issuelinks,comment,project"
        }
        
        response = session.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        issues_data = data.get("issues", [])
        # Validate and return list of JiraIssue models
        return [JiraIssue(**issue) for issue in issues_data]
        
    except Exception as e:
        return [JiraError(error=str(e))]

def jira_get_issue(issue_key: str) -> JiraIssue | JiraError:
    """Get details of a specific Jira issue as a Pydantic model."""
    try:
        session, base_url = _get_jira_session()
        url = f"{base_url}/rest/api/3/issue/{issue_key}"
        
        response = session.get(url)
        response.raise_for_status()
        data = response.json()
        
        return JiraIssue(**data)
        
    except Exception as e:
        return JiraError(error=str(e))

def jira_get_issue_comments(issue_key: str) -> list[JiraComment] | JiraError:
    """Get all comments for a specific Jira issue as a list of Pydantic models."""
    try:
        session, base_url = _get_jira_session()
        url = f"{base_url}/rest/api/3/issue/{issue_key}/comment"
        
        response = session.get(url)
        response.raise_for_status()
        data = response.json()
        
        comments_data = data.get("comments", [])
        return [JiraComment(**comment) for comment in comments_data]
        
    except Exception as e:
        return JiraError(error=str(e))

def jira_get_project(project_key: str) -> JiraProject | JiraError:
    """Get details of a specific Jira project as a Pydantic model."""
    try:
        session, base_url = _get_jira_session()
        url = f"{base_url}/rest/api/3/project/{project_key}"
        
        response = session.get(url)
        response.raise_for_status()
        data = response.json()
        
        return JiraProject(**data)
        
    except Exception as e:
        return JiraError(error=str(e))

def jira_list_projects() -> list[JiraProject] | list[JiraError]:
    """List all visible projects as Pydantic models."""
    try:
        session, base_url = _get_jira_session()
        url = f"{base_url}/rest/api/3/project"
        
        response = session.get(url)
        response.raise_for_status()
        data = response.json()
        
        return [JiraProject(**proj) for proj in data]
        
    except Exception as e:
        return [JiraError(error=str(e))]

def jira_get_recent_projects() -> list[JiraProject] | list[JiraError]:
    """Get the last 20 recent projects with insight details."""
    try:
        session, base_url = _get_jira_session()
        url = f"{base_url}/rest/api/3/project/recent"
        params = {"expand": "insight"}
        
        response = session.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        return [JiraProject(**proj) for proj in data]
        
    except Exception as e:
        return [JiraError(error=str(e))]
