"""
Jira tools definitions for RLM.
"""

JIRA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "jira_search_issues",
            "description": "Search for Jira issues using JQL (Jira Query Language) with Pagination.",
            "parameters": {
                "type": "object",
                "properties": {
                    "jql": {
                        "type": "string",
                        "description": "The JQL query string (e.g., 'project = PROJ AND status = Open')."
                    }, 
                    "startAt": {
                        "type": "integer",
                        "description": "The index of the first issue to return (0-based)."
                    },
                    "maxResults": {
                        "type": "integer",
                        "description": "The maximum number of issues to return (default 20)."
                    },
                    "fields": {"type":"string",
                        "description": "A list of fields to include in the response"
                    }
                },
                "required": ["jql"]
            },
            "returns": "{'jira_issues': list[JiraIssue], 'nextPageToken': str | None} | error"
        }
    },
    {
        "type": "function",
        "function": {
            "name": "jira_get_issue",
            "description": "Get details of a specific Jira issue by its key or ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "The issue key (e.g., 'PROJ-123') or ID."
                    }
                },
                "required": ["issue_key"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "jira_get_issue_comments",
            "description": "Get all comments for a specific Jira issue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "The issue key (e.g., 'PROJ-123') or ID."
                    }
                },
                "required": ["issue_key"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "jira_get_project",
            "description": "Get details of a specific Jira project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_key": {
                        "type": "string",
                        "description": "The project key (e.g., 'PROJ') or ID."
                    }
                },
                "required": ["project_key"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "jira_list_projects",
            "description": "List all visible projects in Jira.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]
