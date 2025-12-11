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
        """Initialize Redis connection"""
        try:
            print(f"🔌 Connecting to Redis at {settings.REDIS_URL}")
            self.client = redis.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD or None,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )

            # Test connection
            await self.client.ping()
            print("✅ Redis connected successfully")

            # Initialize encryption
            key = hashlib.sha256(settings.ENCRYPTION_KEY.encode()).digest()
            fernet_key = base64.urlsafe_b64encode(key[:32])
            self.fernet = Fernet(fernet_key)

        except Exception as e:
            print(f"❌ Failed to connect to Redis: {e}")
            # Create a mock client for development
            self.client = None

    async def close(self):
        if self.client:
            await self.client.aclose()

    async def ping(self):
        """Check Redis connection"""
        try:
            if self.client:
                return await self.client.ping()
            return False
        except:
            return False

    def _encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        if self.fernet:
            return self.fernet.encrypt(data.encode()).decode()
        return data  # Return plaintext if encryption not available

    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if self.fernet:
            return self.fernet.decrypt(encrypted_data.encode()).decode()
        return encrypted_data  # Return as-is if decryption not available

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
            if not self.client:
                print("⚠️ Redis not connected, skipping save")
                return False

            key = self._generate_key(user_id, repo_name)

            data = {
                "token": self._encrypt(token),
                "username": username,
                "repo_name": repo_name,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            # Save repository data
            await self.client.set(
                key,
                json.dumps(data),
                ex=settings.REDIS_TTL
            )
            print(f"✅ Repository data saved: {key}")

            # Also store in user's repository list
            user_key = f"user:{user_id}:repositories"
            await self.client.sadd(user_key, repo_name)
            print(f"✅ Added to user repository list: {user_key}")

            # Set TTL for user key as well
            await self.client.expire(user_key, settings.REDIS_TTL)

            return True
        except Exception as e:
            print(f"❌ Error saving repository: {e}")
            return False

    async def get_repository(
            self,
            user_id: str,
            repo_name: str
    ) -> Optional[Dict]:
        """Get repository data with decrypted token"""
        try:
            if not self.client:
                return None

            key = self._generate_key(user_id, repo_name)
            data = await self.client.get(key)

            if data:
                data_dict = json.loads(data)
                data_dict["token"] = self._decrypt(data_dict["token"])
                return data_dict
            return None
        except Exception as e:
            print(f"❌ Error getting repository: {e}")
            return None

    async def delete_repository(self, user_id: str, repo_name: str) -> bool:
        """Delete repository connection"""
        try:
            if not self.client:
                return False

            key = self._generate_key(user_id, repo_name)

            # Delete repository data
            deleted = await self.client.delete(key)

            # Remove from user's repository list
            user_key = f"user:{user_id}:repositories"
            await self.client.srem(user_key, repo_name)

            return deleted > 0
        except Exception as e:
            print(f"❌ Error deleting repository: {e}")
            return False

    async def get_user_repositories(self, user_id: str) -> List[str]:
        """Get all repositories for a user"""
        try:
            if not self.client:
                return []

            user_key = f"user:{user_id}:repositories"
            repositories = await self.client.smembers(user_key)
            return list(repositories)
        except Exception as e:
            print(f"❌ Error getting user repositories: {e}")
            return []

    async def save_template(
            self,
            user_id: str,
            template_name: str,
            template_data: Dict
    ) -> bool:
        """Save custom template for user"""
        try:
            if not self.client:
                return False

            key = f"user:{user_id}:template:{template_name}"
            await self.client.set(
                key,
                json.dumps(template_data),
                ex=settings.REDIS_TTL * 30  # 30 дней для шаблонов
            )
            return True
        except Exception as e:
            print(f"❌ Error saving template: {e}")
            return False

    async def get_user_templates(self, user_id: str) -> Dict:
        """Get all templates for a user"""
        try:
            if not self.client:
                return {}

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
            print(f"❌ Error getting templates: {e}")
            return {}

    async def get_all_users(self) -> List[str]:
        """Get all user IDs"""
        try:
            if not self.client:
                return []

            pattern = "user:*:repositories"
            keys = await self.client.keys(pattern)
            users = []
            for key in keys:
                # Extract user_id from key pattern: user:{user_id}:repositories
                parts = key.split(":")
                if len(parts) > 1:
                    users.append(parts[1])
            return users
        except Exception as e:
            print(f"❌ Error getting users: {e}")
            return []


redis_client = RedisClient()