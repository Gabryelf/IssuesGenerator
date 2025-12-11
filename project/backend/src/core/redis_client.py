import json
import hashlib
from datetime import datetime
from typing import Optional, List, Dict
import redis.asyncio as redis
from cryptography.fernet import Fernet
import base64

from backend.src.config.settings import settings


class RedisClient:
    def __init__(self):
        self.client = None
        self.fernet = None

    async def initialize(self):
        # Initialize Redis connection
        self.client = redis.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD or None,
            decode_responses=True
        )

        # Initialize encryption
        key = hashlib.sha256(settings.ENCRYPTION_KEY.encode()).digest()
        fernet_key = base64.urlsafe_b64encode(key[:32])
        self.fernet = Fernet(fernet_key)

    async def close(self):
        if self.client:
            await self.client.aclose()

    async def ping(self):
        try:
            return await self.client.ping()
        except:
            return False

    def _encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.fernet.encrypt(data.encode()).decode()

    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.fernet.decrypt(encrypted_data.encode()).decode()

    def _generate_key(self, user_id: str, repo_name: str) -> str:
        """Generate Redis key for repository"""
        return f"user:{user_id}:repo:{repo_name}"

    async def save_repository(
            self,
            user_id: str,
            repo_name: str,
            token: str,
            username: str,
            metadata: Optional[Dict] = None
    ) -> bool:
        """Save repository connection with encrypted token"""
        try:
            key = self._generate_key(user_id, repo_name)

            data = {
                "token": self._encrypt(token),
                "username": username,
                "repo_name": repo_name,
                "metadata": metadata or {},
                "created_at": str(datetime.utcnow())
            }

            await self.client.set(
                key,
                json.dumps(data),
                ex=settings.REDIS_TTL
            )

            # Also store in user's repository list
            user_key = f"user:{user_id}:repositories"
            await self.client.sadd(user_key, repo_name)

            return True
        except Exception as e:
            print(f"Error saving repository: {e}")
            return False

    async def get_repository(
            self,
            user_id: str,
            repo_name: str
    ) -> Optional[Dict]:
        """Get repository data with decrypted token"""
        try:
            key = self._generate_key(user_id, repo_name)
            data = await self.client.get(key)

            if data:
                data_dict = json.loads(data)
                data_dict["token"] = self._decrypt(data_dict["token"])
                return data_dict
            return None
        except Exception as e:
            print(f"Error getting repository: {e}")
            return None

    async def delete_repository(self, user_id: str, repo_name: str) -> bool:
        """Delete repository connection"""
        try:
            key = self._generate_key(user_id, repo_name)
            await self.client.delete(key)

            # Remove from user's repository list
            user_key = f"user:{user_id}:repositories"
            await self.client.srem(user_key, repo_name)

            return True
        except Exception as e:
            print(f"Error deleting repository: {e}")
            return False

    async def get_user_repositories(self, user_id: str) -> List[str]:
        """Get all repositories for a user"""
        try:
            user_key = f"user:{user_id}:repositories"
            repositories = await self.client.smembers(user_key)
            return list(repositories)
        except Exception as e:
            print(f"Error getting user repositories: {e}")
            return []

    async def save_template(
            self,
            user_id: str,
            template_name: str,
            template_data: Dict
    ) -> bool:
        """Save custom template for user"""
        try:
            key = f"user:{user_id}:template:{template_name}"
            await self.client.set(
                key,
                json.dumps(template_data),
                ex=settings.REDIS_TTL * 30  # 30 дней для шаблонов
            )
            return True
        except Exception as e:
            print(f"Error saving template: {e}")
            return False

    async def get_user_templates(self, user_id: str) -> Dict:
        """Get all templates for a user"""
        try:
            pattern = f"user:{user_id}:template:*"
            keys = await self.client.keys(pattern)

            templates = {}
            for key in keys:
                data = await self.client.get(key)
                if data:
                    template_name = key.split(":")[-1]
                    templates[template_name] = json.loads(data)

            return templates
        except Exception as e:
            print(f"Error getting templates: {e}")
            return {}


redis_client = RedisClient()
