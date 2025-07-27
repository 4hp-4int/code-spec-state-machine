"""Semantic caching system using embeddings for similarity matching."""

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class SemanticCache:
    """Semantic cache using embeddings for similarity matching."""
    
    def __init__(self, cache_path: Path, similarity_threshold: float = 0.85, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize semantic cache.
        
        Args:
            cache_path: Path to SQLite cache database
            similarity_threshold: Minimum similarity score for cache hits (0.0-1.0)
            model_name: Sentence transformer model name
        """
        self.cache_path = cache_path
        self.similarity_threshold = similarity_threshold
        self.model_name = model_name
        self._model = None
        self._init_db()
    
    def _get_model(self) -> SentenceTransformer | None:
        """Lazy load the sentence transformer model."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            return None
            
        if self._model is None:
            try:
                self._model = SentenceTransformer(self.model_name)
            except Exception as e:
                print(f"Warning: Failed to load sentence transformer model: {e}")
                return None
        return self._model
    
    def _init_db(self) -> None:
        """Initialize SQLite database with embedding support."""
        with sqlite3.connect(self.cache_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_cache (
                    cache_key TEXT PRIMARY KEY,
                    input_text TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    response_data TEXT NOT NULL,
                    model TEXT NOT NULL,
                    temperature REAL NOT NULL,
                    created_at REAL NOT NULL,
                    ttl_hours INTEGER DEFAULT 24
                )
            """)
            conn.commit()
    
    def _text_to_embedding(self, text: str) -> np.ndarray | None:
        """Convert text to embedding vector."""
        model = self._get_model()
        if model is None:
            return None
            
        try:
            # Generate embedding
            embedding = model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            print(f"Warning: Failed to generate embedding: {e}")
            return None
    
    def _cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings."""
        # Normalize vectors
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        # Calculate cosine similarity
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        return float(similarity)
    
    def get_cached_response(self, input_text: str, model: str, temperature: float = 0.7) -> dict[str, Any] | None:
        """Retrieve semantically similar cached response."""
        embedding = self._text_to_embedding(input_text)
        if embedding is None:
            # Fallback to exact text match if embeddings fail
            return self._get_exact_match(input_text, model, temperature)
        
        with sqlite3.connect(self.cache_path) as conn:
            cursor = conn.execute(
                "SELECT response_data, created_at, ttl_hours, embedding FROM semantic_cache WHERE model = ? AND ABS(temperature - ?) < 0.1",
                (model, temperature)
            )
            
            best_similarity = 0.0
            best_response = None
            expired_keys = []
            
            for row in cursor.fetchall():
                response_data, created_at, ttl_hours, embedding_blob = row
                
                # Check if cache entry is expired
                if time.time() - created_at >= (ttl_hours * 3600):
                    expired_keys.append((response_data, created_at))
                    continue
                
                try:
                    # Deserialize stored embedding
                    cached_embedding = np.frombuffer(embedding_blob, dtype=np.float32)
                    
                    # Calculate similarity
                    similarity = self._cosine_similarity(embedding, cached_embedding)
                    
                    if similarity > best_similarity and similarity >= self.similarity_threshold:
                        best_similarity = similarity
                        best_response = json.loads(response_data)
                        
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    print(f"Warning: Corrupted cache entry: {e}")
                    expired_keys.append((response_data, created_at))
            
            # Clean up expired/corrupted entries
            for response_data, created_at in expired_keys:
                conn.execute(
                    "DELETE FROM semantic_cache WHERE response_data = ? AND created_at = ?",
                    (response_data, created_at)
                )
            conn.commit()
            
            return best_response
    
    def _get_exact_match(self, input_text: str, model: str, temperature: float) -> dict[str, Any] | None:
        """Fallback exact text matching when embeddings aren't available."""
        with sqlite3.connect(self.cache_path) as conn:
            cursor = conn.execute(
                "SELECT response_data, created_at, ttl_hours FROM semantic_cache WHERE input_text = ? AND model = ? AND ABS(temperature - ?) < 0.01",
                (input_text, model, temperature)
            )
            row = cursor.fetchone()
            
            if row:
                response_data, created_at, ttl_hours = row
                if time.time() - created_at < (ttl_hours * 3600):
                    try:
                        return json.loads(response_data)
                    except (json.JSONDecodeError, TypeError):
                        # Remove corrupted entry
                        conn.execute(
                            "DELETE FROM semantic_cache WHERE input_text = ? AND created_at = ?",
                            (input_text, created_at)
                        )
                        conn.commit()
        return None
    
    def store_response(
        self, 
        input_text: str, 
        response_data: dict[str, Any], 
        model: str, 
        temperature: float, 
        ttl_hours: int = 24
    ) -> bool:
        """Store response with embedding in cache."""
        embedding = self._text_to_embedding(input_text)
        if embedding is None:
            print("Warning: Could not generate embedding, skipping cache storage")
            return False
        
        cache_key = self._generate_cache_key(input_text, model, temperature)
        
        with sqlite3.connect(self.cache_path) as conn:
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO semantic_cache 
                       (cache_key, input_text, embedding, response_data, model, temperature, created_at, ttl_hours) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        cache_key,
                        input_text,
                        embedding.tobytes(),
                        json.dumps(response_data),
                        model,
                        temperature,
                        time.time(),
                        ttl_hours
                    )
                )
                conn.commit()
                return True
            except Exception as e:
                print(f"Warning: Failed to store in cache: {e}")
                return False
    
    def _generate_cache_key(self, input_text: str, model: str, temperature: float) -> str:
        """Generate a unique cache key."""
        import hashlib
        key_data = f"{model}:{temperature:.2f}:{hash(input_text)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def clear_expired(self) -> int:
        """Clear expired cache entries and return count of removed entries."""
        with sqlite3.connect(self.cache_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM semantic_cache WHERE ? - created_at >= ttl_hours * 3600",
                (time.time(),)
            )
            count = cursor.fetchone()[0]
            
            conn.execute(
                "DELETE FROM semantic_cache WHERE ? - created_at >= ttl_hours * 3600",
                (time.time(),)
            )
            conn.commit()
            return count
    
    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with sqlite3.connect(self.cache_path) as conn:
            cursor = conn.execute("SELECT COUNT(*), AVG(ttl_hours) FROM semantic_cache")
            total, avg_ttl = cursor.fetchone()
            
            cursor = conn.execute(
                "SELECT COUNT(*) FROM semantic_cache WHERE ? - created_at < ttl_hours * 3600",
                (time.time(),)
            )
            valid_count = cursor.fetchone()[0]
            
            return {
                "total_entries": total or 0,
                "valid_entries": valid_count or 0,
                "expired_entries": (total or 0) - (valid_count or 0),
                "average_ttl_hours": avg_ttl or 0,
                "embeddings_available": SENTENCE_TRANSFORMERS_AVAILABLE,
                "model_name": self.model_name,
                "similarity_threshold": self.similarity_threshold,
            }