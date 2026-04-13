"""
Jira OAuth token refresh and request retry utilities.

Atlassian uses rotating refresh tokens: every successful refresh returns a new
refresh_token that invalidates the previous one. Callers must persist the new
token pair returned by these functions.
"""

import os
import requests
from typing import Any

# Atlassian OAuth token endpoint
ATLASSIAN_TOKEN_URL = "https://auth.atlassian.com/oauth/token"


class JiraTokenRefreshError(Exception):
    """Raised when a token refresh fails irrecoverably (e.g. invalid_grant)."""
    pass


def refresh_jira_token(refresh_token: str) -> dict[str, str]:
    """Exchange a refresh token for a new access + refresh token pair.

    Returns:
        {"access_token": "...", "refresh_token": "..."} on success.

    Raises:
        JiraTokenRefreshError: If the refresh fails (invalid_grant, missing
            client credentials, etc.). The user must re-authenticate.
        ValueError: If required environment variables are missing.
    """
    client_id = os.getenv("JIRA_CLIENT_ID")
    client_secret = os.getenv("JIRA_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError(
            "JIRA_CLIENT_ID and JIRA_CLIENT_SECRET must be set for token refresh."
        )

    payload = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }

    response = requests.post(ATLASSIAN_TOKEN_URL, json=payload)

    if response.status_code != 200:
        error_body = response.text
        print(f"[jira_auth] Token refresh failed ({response.status_code}): {error_body}")
        raise JiraTokenRefreshError(
            f"Token refresh failed ({response.status_code}): {error_body}"
        )

    data = response.json()
    new_access = data.get("access_token")
    new_refresh = data.get("refresh_token")

    if not new_access:
        raise JiraTokenRefreshError("Token refresh response missing access_token.")

    print("[jira_auth] Token refresh succeeded.")
    return {
        "access_token": new_access,
        "refresh_token": new_refresh or refresh_token,
    }


def jira_request_with_retry(
    method: str,
    url: str,
    jira_token: str,
    jira_refresh_token: str | None = None,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> tuple[requests.Response, dict[str, str] | None]:
    """Make a Jira API request with automatic 401 retry via token refresh.

    Args:
        method: HTTP method ("GET", "POST", etc.).
        url: Full Jira API URL.
        jira_token: Current access token.
        jira_refresh_token: Refresh token for retry. If None, 401 is not retried.
        params: Query parameters.
        json_body: JSON body for POST/PUT requests.

    Returns:
        A tuple of (response, new_tokens). new_tokens is None if no refresh
        occurred, or {"access_token": "...", "refresh_token": "..."} if it did.
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {jira_token}",
    }

    response = requests.request(
        method, url, headers=headers, params=params, json=json_body
    )

    if response.status_code == 401 and jira_refresh_token:
        print(f"[jira_auth] Got 401 from {url}, attempting token refresh...")
        try:
            new_tokens = refresh_jira_token(jira_refresh_token)
        except (JiraTokenRefreshError, ValueError) as e:
            print(f"[jira_auth] Refresh failed: {e}")
            return response, None

        # Retry with the new access token
        headers["Authorization"] = f"Bearer {new_tokens['access_token']}"
        response = requests.request(
            method, url, headers=headers, params=params, json=json_body
        )
        return response, new_tokens

    return response, None
