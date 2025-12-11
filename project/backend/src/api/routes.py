from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import requests
import uuid
from datetime import datetime

from backend.src.models.schemas import (
    IssueCreate,
    GitHubIssueRequest,
    RepositoryConnection,
    RepositoryInfo,
    IssueTemplate,
    StandardResponse,
    IssueResponse,
    RepositoriesResponse,
    TemplatesResponse
)
from backend.src.services.github_service import GitHubService
from backend.src.services.template_service import TemplateService
from backend.src.core.redis_client import redis_client

router = APIRouter()
github_service = GitHubService()


@router.post("/verify", response_model=StandardResponse)
async def verify_repository(connection: RepositoryConnection):
    """Verify and optionally save repository connection"""
    print(f"Verifying repository: {connection.username}/{connection.repo_name}")

    result = github_service.verify_token_and_repo(
        connection.token,
        connection.username,
        connection.repo_name
    )

    if not result.get("valid", False):
        raise HTTPException(status_code=401, detail=result.get("message", "Invalid token"))

    if connection.save_to_redis:
        # Generate user ID
        user_id = str(uuid.uuid4())

        # Save to Redis
        await redis_client.save_repository(
            user_id=user_id,
            repo_name=connection.repo_name,
            token=connection.token,
            username=connection.username,
            metadata={
                **connection.metadata,
                "verified_at": datetime.utcnow().isoformat()
            }
        )

    return StandardResponse(
        success=True,
        message=result.get("message", "Verification successful"),
        data={"repo_data": result.get("repo_data")}
    )


@router.get("/verify-token")
async def verify_token_get(
        token: str = Query(..., description="GitHub token"),
        username: str = Query(..., description="GitHub username"),
        repo_name: str = Query(..., description="Repository name")
):
    """GET endpoint for token verification (legacy support)"""
    print(f"GET: Verifying token for {username}/{repo_name}")

    url = f"https://api.github.com/repos/{username}/{repo_name}"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Issues-Creator-Pro"
    }

    try:
        response = requests.get(url, headers=headers)
        print(f"GitHub API response status: {response.status_code}")

        if response.status_code == 200:
            repo_data = response.json()
            return {
                "valid": True,
                "repo_exists": True,
                "message": "Token and repository are valid",
                "repo_data": {
                    "name": repo_data.get("name"),
                    "full_name": repo_data.get("full_name"),
                    "private": repo_data.get("private"),
                    "description": repo_data.get("description"),
                    "stars": repo_data.get("stargazers_count"),
                    "forks": repo_data.get("forks_count"),
                    "open_issues": repo_data.get("open_issues_count"),
                    "default_branch": repo_data.get("default_branch")
                }
            }
        elif response.status_code == 404:
            return {
                "valid": True,
                "repo_exists": False,
                "message": "Repository not found"
            }
        elif response.status_code == 401:
            return {
                "valid": False,
                "repo_exists": False,
                "message": "Invalid token"
            }
        else:
            return {
                "valid": False,
                "repo_exists": False,
                "message": f"GitHub API error: {response.status_code}"
            }

    except Exception as e:
        print(f"Error: {e}")
        return {
            "valid": False,
            "repo_exists": False,
            "message": f"Connection error: {str(e)}"
        }


@router.get("/templates", response_model=TemplatesResponse)
async def get_templates(
        category: Optional[str] = Query(None, description="Filter by category")
):
    """Get available issue templates"""
    templates_dict = TemplateService.get_predefined_templates()

    if category:
        templates = [
            template for template in templates_dict.values()
            if category.lower() in template.name.lower() or
               category.lower() in template.description.lower()
        ]
    else:
        templates = list(templates_dict.values())

    return TemplatesResponse(
        success=True,
        message=f"Found {len(templates)} templates",
        templates=templates
    )


@router.get("/templates/{template_name}", response_model=StandardResponse)
async def get_template_details(template_name: str):
    """Get details of a specific template"""
    template = TemplateService.get_template(template_name)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Get fields as dictionaries
    fields = TemplateService.get_template_fields(template_name)

    return StandardResponse(
        success=True,
        message="Template retrieved successfully",
        data={
            "template": template.dict(),
            "fields": fields
        }
    )


@router.post("/issues/create", response_model=IssueResponse)
async def create_issue(issue_data: GitHubIssueRequest):
    """Create a GitHub issue"""
    print(f"Creating issue in {issue_data.username}/{issue_data.repo_name}")
    print(f"Issue title: {issue_data.title[:50]}...")

    result = github_service.create_issue(
        token=issue_data.token,
        username=issue_data.username,
        repo_name=issue_data.repo_name,
        title=issue_data.title,
        body=issue_data.body,
        labels=issue_data.labels,
        assignees=issue_data.assignees
    )

    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed to create issue"))

    return IssueResponse(
        success=True,
        message=result.get("message", "Issue created successfully"),
        issue_url=result.get("issue_url"),
        data={"issue_number": result.get("issue_number")}
    )


@router.post("/create-issue")
async def create_issue_compat(issue_data: GitHubIssueRequest):
    """Compatibility endpoint for old frontend URLs"""
    print(f"⚠️ Using compatibility endpoint /api/create-issue")
    print(f"Creating issue in {issue_data.username}/{issue_data.repo_name}")
    print(f"Issue title: {issue_data.title[:50]}...")

    # Call the actual create_issue function
    return await create_issue(issue_data)


@router.get("/repositories", response_model=RepositoriesResponse)
async def get_saved_repositories(
        user_id: Optional[str] = Query(None, description="User identifier")
):
    """Get user's saved repositories"""
    if not user_id:
        # In production, get from authentication
        user_id = "default_user"

    repo_names = await redis_client.get_user_repositories(user_id)
    repositories = []

    for repo_name in repo_names:
        repo_data = await redis_client.get_repository(user_id, repo_name)
        if repo_data:
            repositories.append(RepositoryInfo(
                username=repo_data["username"],
                repo_name=repo_data["repo_name"],
                last_used=datetime.fromisoformat(
                    repo_data.get("metadata", {}).get("verified_at", datetime.utcnow().isoformat())),
                metadata=repo_data.get("metadata", {})
            ))

    return RepositoriesResponse(
        success=True,
        message=f"Found {len(repositories)} saved repositories",
        repositories=repositories
    )


@router.delete("/repositories/{repo_name}", response_model=StandardResponse)
async def delete_repository(
        repo_name: str,
        user_id: Optional[str] = Query(None, description="User identifier")
):
    """Delete saved repository connection"""
    if not user_id:
        user_id = "default_user"

    success = await redis_client.delete_repository(user_id, repo_name)

    if success:
        return StandardResponse(
            success=True,
            message=f"Repository '{repo_name}' deleted successfully"
        )
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Repository '{repo_name}' not found or could not be deleted"
        )


@router.post("/templates/custom", response_model=StandardResponse)
async def save_custom_template(
        template: IssueTemplate,
        user_id: Optional[str] = Query(None, description="User identifier")
):
    """Save custom template"""
    if not user_id:
        user_id = "default_user"

    success = await redis_client.save_template(
        user_id=user_id,
        template_name=template.name,
        template_data=template.dict()
    )

    if success:
        return StandardResponse(
            success=True,
            message=f"Template '{template.name}' saved successfully"
        )
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to save template"
        )


@router.get("/user/templates", response_model=StandardResponse)
async def get_user_templates(
        user_id: Optional[str] = Query(None, description="User identifier")
):
    """Get user's custom templates"""
    if not user_id:
        user_id = "default_user"

    templates_dict = await redis_client.get_user_templates(user_id)

    # Convert dict values to list
    templates_list = list(templates_dict.values()) if templates_dict else []

    return StandardResponse(
        success=True,
        message=f"Found {len(templates_list)} custom templates",
        data={"templates": templates_list}
    )


@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify API is working"""
    return {
        "status": "ok",
        "message": "GitHub Issues Creator Pro API is running",
        "version": "2.0.0",
        "endpoints": [
            {"method": "POST", "path": "/api/verify", "description": "Verify repository connection"},
            {"method": "GET", "path": "/api/verify-token", "description": "Verify token (GET)"},
            {"method": "GET", "path": "/api/templates", "description": "Get all templates"},
            {"method": "GET", "path": "/api/templates/{name}", "description": "Get template details"},
            {"method": "POST", "path": "/api/issues/create", "description": "Create issue"},
            {"method": "POST", "path": "/api/create-issue", "description": "Create issue (compatibility)"},
            {"method": "GET", "path": "/api/repositories", "description": "Get saved repositories"},
            {"method": "DELETE", "path": "/api/repositories/{name}", "description": "Delete repository"},
        ]
    }
