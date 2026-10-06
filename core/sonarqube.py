"""SonarQube client for the CodeSentinel code review agent.

Provides functionality to query SonarQube for code issues and normalize
them into Finding objects compatible with the agents/base.py Finding class.
"""

from __future__ import annotations

import requests
from typing import List

from agents.base import Finding
from core.config import Settings


def get_issues(project_key: str, pull_request: int) -> List[Finding]:
    """Query SonarQube API for issues related to a project/pull request.

    Args:
        project_key: The SonarQube project key (e.g., "myproject").
        pull_request: The pull request number (included for compatibility;
                     SonarQube issue search uses project_key primarily).

    Returns:
        A list of Finding objects representing SonarQube issues.
        Returns an empty list on API errors or no issues found.
    """
    settings = Settings()

    url = f"{settings.sonarqube_url.rstrip('/')}/api/issues/search"
    params = {
        "component": project_key,
        "qualifiers": "+SONAR:issue",
    }

    # Safely extract token value - SecretStr may be auto-decoded from env vars
    token_value = (
        settings.sonarqube_token.get_secret_value()
        if hasattr(settings.sonarqube_token, "get_secret_value")
        else str(settings.sonarqube_token)
    )

    try:
        response = requests.get(
            url,
            params=params,
            headers={
                "Authorization": f"Bearer {token_value}",
            },
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException:
        # Gracefully handle any API request errors
        return []

    try:
        data = response.json()
    except ValueError:
        # Gracefully handle non-JSON responses
        return []

    issues: List[Finding] = []

    for issue in data.get("issues", []):
        # Extract severity from SonarQube
        severity = issue.get("severity", "INFO").upper()

        # Extract title/description from message
        title = issue.get("message", "SonarQube issue")
        description = issue.get("message", "")

        # Extract file path from component or file field
        component = issue.get("component", "")
        file_path: str | None = None
        if component:
            # Component format can be "projectKey:path/to/file.py" or "path/to/file.py"
            # Extract the file path part after the colon if present
            if ":" in component:
                file_path = component.split(":", 1)[1]
            else:
                file_path = component

        # Extract line number from text_line
        line_number = issue.get("text_line", issue.get("line"))
        if isinstance(line_number, str):
            try:
                line_number = int(line_number)
            except ValueError:
                line_number = None

        finding = Finding(
            severity=severity,
            title=title,
            description=description,
            file_path=file_path,
            line_number=line_number,
        )
        issues.append(finding)

    return issues