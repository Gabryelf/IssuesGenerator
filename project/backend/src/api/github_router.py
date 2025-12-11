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
    print(f"📡 Verifying repository: {connection.username}/{connection.repo_name}")
    print(f"🔐 Save to Redis: {connection.save_to_redis}")

    result = github_service.verify_token_and_repo(
        connection.token,
        connection.username,
        connection.repo_name
    )

    if not result.get("valid", False):
        raise HTTPException(status_code=401, detail=result.get("message", "Invalid token"))

    if connection.save_to_redis:
        # Use provided user_id or generate one
        user_id = connection.metadata.get("user_id") if connection.metadata else None
        if not user_id:
            user_id = str(uuid.uuid4())
            print(f"🔑 Generated user_id: {user_id}")

        # Prepare metadata
        metadata = connection.metadata or {}
        metadata.update({
            "verified_at": datetime.utcnow().isoformat(),
            "saved_at": datetime.utcnow().isoformat(),
            "user_id": user_id
        })

        # Save to Redis
        saved = await redis_client.save_repository(
            user_id=user_id,
            repo_name=connection.repo_name,
            token=connection.token,
            username=connection.username,
            metadata=metadata
        )

        if saved:
            print(f"✅ Repository saved to Redis for user {user_id}")

            # Also verify that it was saved
            saved_data = await redis_client.get_repository(user_id, connection.repo_name)
            if saved_data:
                print(f"📦 Confirmed repository saved: {saved_data['repo_name']}")
            else:
                print(f"⚠️ Warning: Repository may not have been saved correctly")
        else:
            print(f"❌ Failed to save repository to Redis")

        # Return user_id in response
        return StandardResponse(
            success=True,
            message=result.get("message", "Verification and save successful"),
            data={
                "repo_data": result.get("repo_data"),
                "user_id": user_id,
                "saved": saved
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
    print(f"📝 Creating issue in {issue_data.username}/{issue_data.repo_name}")
    print(f"📌 Issue title: {issue_data.title[:50]}...")

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
    print(f"📡 Getting repositories for user_id: {user_id}")

    if not user_id:
        # Try to get from default
        user_id = "default_user"
        print(f"⚠️ No user_id provided, using default: {user_id}")

    try:
        repo_names = await redis_client.get_user_repositories(user_id)
        print(f"📦 Found repository names: {repo_names}")

        repositories = []

        for repo_name in repo_names:
            repo_data = await redis_client.get_repository(user_id, repo_name)
            if repo_data:
                print(f"✅ Loaded repository data: {repo_name}")
                repositories.append(RepositoryInfo(
                    username=repo_data["username"],
                    repo_name=repo_data["repo_name"],
                    last_used=datetime.fromisoformat(
                        repo_data.get("metadata", {}).get("verified_at", datetime.utcnow().isoformat())),
                    metadata=repo_data.get("metadata", {})
                ))

        print(f"✅ Total repositories loaded: {len(repositories)}")
        return RepositoriesResponse(
            success=True,
            message=f"Found {len(repositories)} saved repositories",
            repositories=repositories
        )
    except Exception as e:
        print(f"❌ Error getting repositories: {e}")
        return RepositoriesResponse(
            success=False,
            message=f"Error getting repositories: {str(e)}",
            repositories=[]
        )


@router.delete("/repositories/{repo_name}", response_model=StandardResponse)
async def delete_repository(
        repo_name: str,
        user_id: Optional[str] = Query(None, description="User identifier")
):
    """Delete saved repository connection"""
    if not user_id:
        user_id = "default_user"

    print(f"🗑️ Deleting repository {repo_name} for user {user_id}")

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


@router.get("/repositories/check", response_model=StandardResponse)
async def check_repositories():
    """Check if any repositories are saved"""
    try:
        # Get all repository keys
        pattern = "user:*:repositories"
        keys = await redis_client.client.keys(pattern)

        repositories_count = 0
        users_count = 0

        for key in keys:
            repos = await redis_client.client.smembers(key)
            repositories_count += len(repos)
            users_count += 1

        return StandardResponse(
            success=True,
            message=f"Found {repositories_count} saved repositories across {users_count} users",
            data={
                "count": repositories_count,
                "users": users_count,
                "status": "redis_connected"
            }
        )
    except Exception as e:
        print(f"❌ Error checking repositories: {e}")
        return StandardResponse(
            success=False,
            message=f"Error checking repositories: {str(e)}",
            data={"count": 0, "status": "redis_error"}
        )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis connection
        redis_ok = await redis_client.ping()

        # Check GitHub API (basic check)
        github_ok = True
        try:
            response = requests.get("https://api.github.com", timeout=5)
            github_ok = response.status_code == 200
        except:
            github_ok = False

        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "redis": "connected" if redis_ok else "disconnected",
                "github_api": "available" if github_ok else "unavailable"
            },
            "version": "2.0.0"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify API is working"""
    # Check Redis
    redis_status = "connected" if await redis_client.ping() else "disconnected"

    return {
        "status": "ok",
        "message": "GitHub Issues Creator Pro API is running",
        "version": "2.0.0",
        "redis": redis_status,
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": [
            {"method": "POST", "path": "/api/verify", "description": "Verify repository connection"},
            {"method": "GET", "path": "/api/verify-token", "description": "Verify token (GET)"},
            {"method": "GET", "path": "/api/templates", "description": "Get all templates"},
            {"method": "GET", "path": "/api/templates/{name}", "description": "Get template details"},
            {"method": "POST", "path": "/api/issues/create", "description": "Create issue"},
            {"method": "POST", "path": "/api/create-issue", "description": "Create issue (compatibility)"},
            {"method": "GET", "path": "/api/repositories", "description": "Get saved repositories"},
            {"method": "DELETE", "path": "/api/repositories/{name}", "description": "Delete repository"},
            {"method": "GET", "path": "/api/health", "description": "Health check"},
            {"method": "GET", "path": "/api/repositories/check", "description": "Check repositories"},
        ]
    }