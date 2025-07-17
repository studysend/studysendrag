import os
import json
import redis
import hashlib
from typing import Any, Optional, List, Dict, Union
from datetime import timedelta
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class RedisService:
    def __init__(self):
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.enabled = os.getenv('REDIS_ENABLED', 'true').lower() == 'true'
        
        if self.enabled:
            try:
                self.client = redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                # Test connection
                self.client.ping()
                logger.info(f"Redis connected successfully to {self.redis_url}")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Caching disabled.")
                self.enabled = False
                self.client = None
        else:
            logger.info("Redis caching disabled")
            self.client = None
    
    def _generate_key(self, prefix: str, *args) -> str:
        """Generate a consistent cache key"""
        key_parts = [str(arg) for arg in args]
        key_string = ":".join([prefix] + key_parts)
        return key_string
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value for Redis storage"""
        if isinstance(value, (str, int, float)):
            return str(value)
        return json.dumps(value, default=str)
    
    def _deserialize_value(self, value: str, value_type: str = "auto") -> Any:
        """Deserialize value from Redis"""
        if not value:
            return None
        
        if value_type == "json":
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        elif value_type == "int":
            try:
                return int(value)
            except ValueError:
                return value
        elif value_type == "float":
            try:
                return float(value)
            except ValueError:
                return value
        else:
            # Auto-detect type
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
    
    def get(self, key: str, value_type: str = "auto") -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled or not self.client:
            return None
        
        try:
            value = self.client.get(key)
            if value is None:
                return None
            return self._deserialize_value(value, value_type)
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL (seconds)"""
        if not self.enabled or not self.client:
            return False
        
        try:
            serialized_value = self._serialize_value(value)
            if ttl:
                return self.client.setex(key, ttl, serialized_value)
            else:
                return self.client.set(key, serialized_value)
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.enabled or not self.client:
            return False
        
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self.enabled or not self.client:
            return 0
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis DELETE_PATTERN error for pattern {pattern}: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.enabled or not self.client:
            return False
        
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter"""
        if not self.enabled or not self.client:
            return None
        
        try:
            return self.client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis INCREMENT error for key {key}: {e}")
            return None
    
    def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key"""
        if not self.enabled or not self.client:
            return False
        
        try:
            return bool(self.client.expire(key, ttl))
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False
    
    # Specialized caching methods for our application
    
    def cache_embedding(self, text: str, embedding: List[float], ttl: int = 86400) -> bool:
        """Cache OpenAI embedding (24 hour TTL by default)"""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        key = self._generate_key("embedding", text_hash)
        return self.set(key, embedding, ttl)
    
    def get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached OpenAI embedding"""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        key = self._generate_key("embedding", text_hash)
        result = self.get(key, "json")
        return result if isinstance(result, list) else None
    
    def cache_course_info(self, course_id: int, course_info: Dict, ttl: int = 3600) -> bool:
        """Cache course information (1 hour TTL)"""
        key = self._generate_key("course", course_id)
        return self.set(key, course_info, ttl)
    
    def get_cached_course_info(self, course_id: int) -> Optional[Dict]:
        """Get cached course information"""
        key = self._generate_key("course", course_id)
        return self.get(key, "json")
    
    def cache_course_documents(self, course_id: int, documents: List[Dict], ttl: int = 1800) -> bool:
        """Cache course documents (30 minutes TTL)"""
        key = self._generate_key("course_docs", course_id)
        return self.set(key, documents, ttl)
    
    def get_cached_course_documents(self, course_id: int) -> Optional[List[Dict]]:
        """Get cached course documents"""
        key = self._generate_key("course_docs", course_id)
        return self.get(key, "json")
    
    def cache_similarity_search(self, query_hash: str, course_id: int, results: List[Dict], ttl: int = 600) -> bool:
        """Cache similarity search results (10 minutes TTL)"""
        key = self._generate_key("search", query_hash, course_id)
        return self.set(key, results, ttl)
    
    def get_cached_similarity_search(self, query_hash: str, course_id: int) -> Optional[List[Dict]]:
        """Get cached similarity search results"""
        key = self._generate_key("search", query_hash, course_id)
        return self.get(key, "json")
    
    def cache_chat_session(self, session_id: int, session_data: Dict, ttl: int = 7200) -> bool:
        """Cache chat session data (2 hours TTL)"""
        key = self._generate_key("session", session_id)
        return self.set(key, session_data, ttl)
    
    def get_cached_chat_session(self, session_id: int) -> Optional[Dict]:
        """Get cached chat session data"""
        key = self._generate_key("session", session_id)
        return self.get(key, "json")
    
    def invalidate_course_cache(self, course_id: int) -> int:
        """Invalidate all cache entries for a course"""
        patterns = [
            f"course:{course_id}",
            f"course_docs:{course_id}",
            f"search:*:{course_id}"
        ]
        
        total_deleted = 0
        for pattern in patterns:
            total_deleted += self.delete_pattern(pattern)
        
        logger.info(f"Invalidated {total_deleted} cache entries for course {course_id}")
        return total_deleted
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics"""
        if not self.enabled or not self.client:
            return {"enabled": False}
        
        try:
            info = self.client.info()
            return {
                "enabled": True,
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "0B"),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": round(
                    info.get("keyspace_hits", 0) / 
                    max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1) * 100, 2
                )
            }
        except Exception as e:
            logger.error(f"Error getting Redis stats: {e}")
            return {"enabled": True, "error": str(e)}

# Global Redis instance
redis_service = RedisService()