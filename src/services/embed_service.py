import logging
from typing import List, Tuple, Optional, Any
import numpy as np

from core.interfaces import VectorDatabase, EmbeddingProvider

logger = logging.getLogger(__name__)

class EmbedService:
    """Service for embedding and similarity search using vector database."""

    def __init__(self, vector_db: VectorDatabase, embedding_provider: EmbeddingProvider):
        """
        Initializes the EmbedService with a VectorDatabase and EmbeddingProvider instances.
        Performs initialization of the vector database (connects, creates extension and table).
        """
        self.vector_db = vector_db
        self.embedding_provider = embedding_provider
        # Initialize the vector database
        try:
            self.vector_db.connect()
            self.vector_db.create_extension()
            self.vector_db.create_table()
            logger.info("Vector database initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize vector database: {e}")
            raise

    def embed_entity(self, entity_name: str, description: str) -> Optional[List[float]]:
        """Embeds an entity description and stores it in PgVector."""
        if not self.vector_db.is_connected():
            logger.error("Vector database is not connected.")
            return None
        try:
            entity_name_embedding = self.embedding_provider.get_embedding(entity_name)
            description_embedding = self.embedding_provider.get_embedding(description)

            if entity_name_embedding and description_embedding:
                self.vector_db.insert_embedding(
                    entity_name,
                    np.array(entity_name_embedding),
                    description,
                    np.array(description_embedding)
                )
                logger.info(f"  Embedding stored for entity: {entity_name}")
                return description_embedding  # Return description embedding
            else:
                logger.warning(f"  Failed to generate embedding for entity: {entity_name}. Not storing in PgVector.")
                return None
        except Exception as e:
            logger.error(f"  Error embedding entity '{entity_name}': {e}")
            return None

    def remove_entity(self, entity_name: str) -> bool:
        """Removes an entity embedding from PgVector."""
        if not self.vector_db.is_connected():
            logger.error("Vector database is not connected.")
            return False
        try:
            self.vector_db.delete_embedding(entity_name)
            logger.info(f"Embedding removed for entity: {entity_name}")
            return True
        except Exception as e:
            logger.error(f"Error removing entity '{entity_name}': {e}")
            return False

    def find_similar_entities_by_entity_name(self, entity_name: str, limit: int = 5) -> Optional[List[Tuple[str, str, float]]]:
        """
        Finds entities with entity_name_embeddings similar to the given entity name.

        Returns a list of tuples, where each tuple contains (entity_name, description, distance).
        """
        if not self.vector_db.is_connected():
            logger.error("Vector database is not connected.")
            return None
        try:
            name_embedding = self.embedding_provider.get_embedding(entity_name)
            if name_embedding:
                similar_entities = self.vector_db.get_nearest_neighbors_by_entity_name(np.array(name_embedding), limit=limit)
                if similar_entities:
                    logger.info(f"Found {len(similar_entities)} similar entities by name for: {entity_name}")
                    return similar_entities
                else:
                    logger.info(f"No similar entities found for: {entity_name}")
                    return None
            else:
                logger.warning(f"Failed to generate embedding for entity: {entity_name}. Cannot find similar entities.")
                return None
        except Exception as e:
            logger.error(f"Error finding similar entities for '{entity_name}': {e}")
            return None

    def find_similar_entities_by_description(self, entity_name: str, description: str, limit: int = 5) -> Optional[List[Tuple[str, str, float]]]:
        """
        Finds entities with embeddings similar to the given entity description.

        Returns a list of tuples, where each tuple contains (entity_name, description, distance).
        """
        if not self.vector_db.is_connected():
            logger.error("Vector database is not connected.")
            return None
        try:
            description_embedding = self.embedding_provider.get_embedding(description)
            if description_embedding:
                similar_entities = self.vector_db.get_nearest_neighbors_by_description(np.array(description_embedding), limit=limit)
                if similar_entities:
                    logger.info(f"Found {len(similar_entities)} similar entities for: {entity_name}")
                    return similar_entities
                else:
                    logger.info(f"No similar entities found for: {entity_name}")
                    return None
            else:
                logger.warning(f"Failed to generate embedding for entity: {entity_name}. Cannot find similar entities.")
                return None
        except Exception as e:
            logger.error(f"Error finding similar entities for '{entity_name}': {e}")
            return None
