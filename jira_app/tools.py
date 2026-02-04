"""
Jira tools definitions for RLM.
"""

JIRA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "jira_search_issues",
            "description": "Search for Jira issues using JQL (Jira Query Language).",
            "parameters": {
                "type": "object",
                "properties": {
                    "jql": {
                        "type": "string",
                        "description": "The JQL query string (e.g., 'project = PROJ AND status = Open')."
                    }, 
                    "fields": {"type":"string",
                        "description": "A list of fields to include in the response"
                    }
                },
                "required": ["jql"]
            }
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
