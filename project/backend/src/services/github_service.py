import requests
from typing import Dict, List, Optional
from backend.src.config.settings import settings


class GitHubService:
    """Service for interacting with GitHub API"""

    def __init__(self):
        self.base_url = settings.GITHUB_API_URL

    def verify_token_and_repo(
            self,
            token: str,
            username: str,
            repo_name: str
    ) -> Dict:
        """Verify GitHub token and repository access"""
        headers = self._create_headers(token)

        print(f"🔍 Verifying token for user: {username}")

        # Check token validity by getting user info
        try:
            user_response = requests.get(
                f"{self.base_url}/user",
                headers=headers,
                timeout=10
            )

            if user_response.status_code != 200:
                print(f"❌ Token invalid: {user_response.status_code}")
                return {
                    "valid": False,
                    "repo_exists": False,
                    "message": f"Invalid token (HTTP {user_response.status_code})"
                }

            user_data = user_response.json()
            print(f"✅ Token valid for user: {user_data.get('login')}")

        except requests.exceptions.RequestException as e:
            print(f"❌ Error checking token: {e}")
            return {
                "valid": False,
                "repo_exists": False,
                "message": f"Network error: {str(e)}"
            }

        # Check repository access
        try:
            repo_response = requests.get(
                f"{self.base_url}/repos/{username}/{repo_name}",
                headers=headers,
                timeout=10
            )

            print(f"📦 Repository check status: {repo_response.status_code}")

            if repo_response.status_code == 200:
                repo_data = repo_response.json()
                print(f"✅ Repository found: {repo_data.get('full_name')}")

                return {
                    "valid": True,
                    "repo_exists": True,
                    "message": "Token and repository are valid",
                    "repo_data": {
                        "name": repo_data.get("name"),
                        "full_name": repo_data.get("full_name"),
                        "private": repo_data.get("private"),
                        "description": repo_data.get("description"),
                        "stars": repo_data.get("stargazers_count", 0),
                        "forks": repo_data.get("forks_count", 0),
                        "open_issues": repo_data.get("open_issues_count", 0),
                        "default_branch": repo_data.get("default_branch"),
                        "owner": repo_data.get("owner", {}).get("login"),
                        "html_url": repo_data.get("html_url")
                    }
                }
            elif repo_response.status_code == 404:
                print(f"❌ Repository not found: {username}/{repo_name}")
                return {
                    "valid": True,
                    "repo_exists": False,
                    "message": f"Repository '{repo_name}' not found for user '{username}'"
                }
            elif repo_response.status_code == 403:
                print(f"❌ Access forbidden (rate limit or permissions)")
                error_data = repo_response.json()
                return {
                    "valid": True,
                    "repo_exists": False,
                    "message": f"Access forbidden: {error_data.get('message', 'Check permissions')}"
                }
            else:
                print(f"❌ Unexpected status: {repo_response.status_code}")
                error_data = repo_response.json()
                return {
                    "valid": True,
                    "repo_exists": False,
                    "message": f"GitHub API error: {repo_response.status_code} - {error_data.get('message', 'Unknown error')}"
                }

        except requests.exceptions.RequestException as e:
            print(f"❌ Error checking repository: {e}")
            return {
                "valid": True,
                "repo_exists": False,
                "message": f"Network error: {str(e)}"
            }

    def create_issue(
            self,
            token: str,
            username: str,
            repo_name: str,
            title: str,
            body: str,
            labels: Optional[List[str]] = None,
            assignees: Optional[List[str]] = None
    ) -> Dict:
        """Create a GitHub issue"""
        url = f"{self.base_url}/repos/{username}/{repo_name}/issues"
        headers = self._create_headers(token)

        print(f"📝 Creating issue in {username}/{repo_name}")
        print(f"📌 Title: {title}")
        print(f"📄 Body preview: {body[:100]}...")

        data = {
            "title": title,
            "body": body
        }

        if labels:
            data["labels"] = labels
            print(f"🏷️  Labels: {labels}")

        if assignees:
            data["assignees"] = assignees
            print(f"👤 Assignees: {assignees}")

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            print(f"📤 Response status: {response.status_code}")

            if response.status_code == 201:
                issue_data = response.json()
                print(f"✅ Issue created: #{issue_data.get('number')}")
                print(f"🔗 Issue URL: {issue_data.get('html_url')}")

                return {
                    "success": True,
                    "issue_url": issue_data["html_url"],
                    "issue_number": issue_data["number"],
                    "message": "Issue created successfully!"
                }
            else:
                error_message = response.json().get('message', 'Unknown error')
                error_details = response.json().get('errors', [])
                print(f"❌ GitHub API error: {response.status_code} - {error_message}")

                if error_details:
                    print(f"📋 Error details: {error_details}")

                return {
                    "success": False,
                    "message": f"GitHub API error: {response.status_code} - {error_message}"
                }
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            return {
                "success": False,
                "message": f"Request error: {str(e)}"
            }
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return {
                "success": False,
                "message": f"Unexpected error: {str(e)}"
            }

    def get_repository_info(
            self,
            token: str,
            username: str,
            repo_name: str
    ) -> Optional[Dict]:
        """Get repository information"""
        url = f"{self.base_url}/repos/{username}/{repo_name}"
        headers = self._create_headers(token)

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None

    def get_user_repositories(
            self,
            token: str,
            username: str
    ) -> List[Dict]:
        """Get user's repositories"""
        url = f"{self.base_url}/user/repos"
        headers = self._create_headers(token)

        try:
            response = requests.get(url, headers=headers, params={
                "per_page": 100,
                "sort": "updated"
            }, timeout=10)

            if response.status_code == 200:
                return response.json()
        except:
            pass
        return []

    def _create_headers(self, token: str) -> Dict:
        """Create headers for GitHub API requests"""
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Issues-Creator-Pro/2.0.0",
            "X-GitHub-Api-Version": "2022-11-28"
        }
