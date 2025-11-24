from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="GitHub Issues Creator")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend files
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


class IssueRequest(BaseModel):
    title: str
    body: str
    token: str
    username: str
    repo_name: str


class StyleConfig(BaseModel):
    bold: bool = False
    italic: bool = False
    code: bool = False
    list_type: str = "bullet"  # "bullet" or "number"


@app.post("/api/create-issue")
async def create_issue(issue_data: IssueRequest):
    """
    Create a GitHub issue
    """
    url = f"https://api.github.com/repos/{issue_data.username}/{issue_data.repo_name}/issues"

    headers = {
        "Authorization": f"token {issue_data.token}",
        "Accept": "application/vnd.github.v3+json"
    }

    data = {
        "title": issue_data.title,
        "body": issue_data.body
    }

    try:
        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 201:
            return {
                "success": True,
                "issue_url": response.json()["html_url"],
                "message": "Issue created successfully!"
            }
        else:
            return {
                "success": False,
                "message": f"Error: {response.status_code} - {response.json().get('message', 'Unknown error')}"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/verify-token")
async def verify_token(token: str, username: str, repo_name: str):
    """
    Verify GitHub token and repository access
    """
    url = f"https://api.github.com/repos/{username}/{repo_name}"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        response = requests.get(url, headers=headers)
        return {
            "valid": response.status_code == 200,
            "repo_exists": response.status_code == 200
        }
    except:
        return {"valid": False, "repo_exists": False}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
