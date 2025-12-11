from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
import os

app = FastAPI(title="GitHub Issues Creator")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend files from the frontend directory
app.mount("/static", StaticFiles(directory="frontend"), name="static")


class IssueRequest(BaseModel):
    title: str
    body: str
    token: str
    username: str
    repo_name: str


class TokenVerification(BaseModel):
    token: str
    username: str
    repo_name: str


@app.get("/")
async def read_index():
    return FileResponse("frontend/index.html")


@app.get("/styles.css")
async def read_css():
    return FileResponse("frontend/styles.css")


@app.get("/script.js")
async def read_js():
    return FileResponse("frontend/script.js")


@app.get("/api/verify-token")
async def verify_token_get(token: str, username: str, repo_name: str):
    """
    GET endpoint for token verification
    """
    print(f"Verifying token for {username}/{repo_name}")

    url = f"https://api.github.com/repos/{username}/{repo_name}"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Issues-Creator"
    }

    try:
        response = requests.get(url, headers=headers)
        print(f"GitHub API response status: {response.status_code}")

        if response.status_code == 200:
            return {
                "valid": True,
                "repo_exists": True,
                "message": "Token and repository are valid"
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


@app.post("/api/create-issue")
async def create_issue(issue_data: IssueRequest):
    """
    Create a GitHub issue
    """
    print(f"Creating issue in {issue_data.username}/{issue_data.repo_name}")

    url = f"https://api.github.com/repos/{issue_data.username}/{issue_data.repo_name}/issues"

    headers = {
        "Authorization": f"token {issue_data.token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Issues-Creator"
    }

    data = {
        "title": issue_data.title,
        "body": issue_data.body
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"Create issue response: {response.status_code}")

        if response.status_code == 201:
            return {
                "success": True,
                "issue_url": response.json()["html_url"],
                "message": "Issue created successfully!"
            }
        else:
            error_message = response.json().get('message', 'Unknown error')
            print(f"Error details: {error_message}")
            return {
                "success": False,
                "message": f"Error: {response.status_code} - {error_message}"
            }

    except Exception as e:
        print(f"Error creating issue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Service is running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
