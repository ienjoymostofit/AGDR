import logging
import random
import hashlib
from typing import Tuple, Any, List
from core.config import ModelConfig
from core.interfaces import EmbeddingProvider

class MockEmbedder(EmbeddingProvider):
    """Mock implementation of the EmbeddingProvider interface for testing."""
    
    def __init__(self, model_config: ModelConfig):
        self.model_config = model_config
        self.embedding_cache = {}
        self.logger = logging.getLogger(__name__)
        self.vector_dimension = 1536  # Standard OpenAI embedding dimension
    
    def _generate_deterministic_embedding(self, text: str) -> List[float]:
        """Generate a deterministic embedding based on the text hash."""
        # Use text hash as seed for random generator to ensure deterministic output
        text_hash = hashlib.md5(text.encode()).hexdigest()
        seed = int(text_hash, 16) % (2**32)
        random.seed(seed)
        
        # Generate a random embedding vector
        embedding = [random.uniform(-1, 1) for _ in range(self.vector_dimension)]
        
        # Normalize the vector
        magnitude = sum(x**2 for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x/magnitude for x in embedding]
            
        return embedding
    
    def get_embedding(self, text: str) -> List[float]:
        """Get a mock embedding for the given text."""
        if text in self.embedding_cache:
            self.logger.debug("Cache hit")
            return self.embedding_cache[text]
        
        self.logger.debug(f"Generating mock embedding for text: {text}")
        embedding = self._generate_deterministic_embedding(text)
        self.embedding_cache[text] = embedding
        return embedding
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate the cosine similarity between two vectors."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        return dot_product / (norm1 * norm2) if norm1 * norm2 > 0 else 0
    
    def compare_texts_cosine(self, text1: str, text2: str) -> float:
        """Compare two texts using cosine similarity of their embeddings."""
        embedding1 = self.get_embedding(text1)
        embedding2 = self.get_embedding(text2)
        similarity = self.cosine_similarity(embedding1, embedding2)
        return similarity
    
    def is_same_concept(self, text1: str, text2: str) -> bool:
        """Determine if two texts refer to the same concept."""
        # For similar texts like "Sweden" and "Swedish", return True
        text1_lower = text1.strip().lower()
        text2_lower = text2.strip().lower()
        
        # Simple heuristic: if one is a substring of the other or they share a common prefix
        if text1_lower in text2_lower or text2_lower in text1_lower:
            return True
        
        # For texts that should be considered the same concept
        if (text1_lower == "sweden" and text2_lower == "swedish") or \
           (text1_lower == "nazi germany" and text2_lower == "germany") or \
           (text1_lower == "world war ii" and text2_lower == "ww2"):
            return True
            
        # Otherwise, use embedding similarity
        similarity = self.compare_texts_cosine(text1, text2)
        return similarity > 0.85  # Higher threshold for mock implementation