import logging
from typing import List, Tuple, Optional
import numpy as np

from clients.pgvector import PgVectorClient
from services.embedder import Embedder

logger = logging.getLogger(__name__)

class PgVectorService:
    """Service for embedding and similarity search using PgVector."""

    def __init__(self, pgvector_client: PgVectorClient, embedder: Embedder):
        """
        Initializes the PgVectorService with PgVectorClient and Embedder instances.
        Performs initialization of PgVectorClient (connects, creates extension and table).
        """
        self.pgvector_client = pgvector_client
        self.embedder = embedder
        # Initialize the PgVectorClient
        try:
            self.pgvector_client.connect()
            self.pgvector_client.create_extension()
            self.pgvector_client.create_table()
            logger.info("PgVectorClient initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize PgVectorClient: {e}")
            raise

    def embed_entity(self, entity_name: str, description: str) -> Optional[List[float]]:
        """Embeds an entity description and stores it in PgVector."""
        if not self.pgvector_client.is_connected():
            logger.error("PgVectorClient is not connected.")
            return None
        try:
            embedding = self.embedder.get_embedding(description)
            if embedding:
                self.pgvector_client.insert_embedding(entity_name, description, np.array(embedding))
                logger.info(f"Embedding stored for entity: {entity_name}")
                return embedding
            else:
                logger.warning(f"Failed to generate embedding for entity: {entity_name}. Not storing in PgVector.")
                return None
        except Exception as e:
            logger.error(f"Error embedding entity '{entity_name}': {e}")
            return None

    def find_similar_entities(self, entity_name: str, description: str, limit: int = 5) -> Optional[List[Tuple[str, str, float]]]:
        """
        Finds entities with embeddings similar to the given entity description.

        Returns a list of tuples, where each tuple contains (entity_name, description, distance).
        """
        if not self.pgvector_client.is_connected():
            logger.error("PgVectorClient is not connected.")
            return None
        try:
            embedding = self.embedder.get_embedding(description)
            if embedding:
                similar_entities = self.pgvector_client.get_nearest_neighbors(np.array(embedding), limit=limit)
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
