import logging
from typing import List, Tuple, Optional
import numpy as np

from clients.pgvector import PgVectorClient
from services.embedder import Embedder

logger = logging.getLogger(__name__)

class EmbedService:
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
            entity_name_embedding = self.embedder.get_embedding(entity_name)
            description_embedding = self.embedder.get_embedding(description)

            if entity_name_embedding and description_embedding:
                self.pgvector_client.insert_embedding(
                    entity_name,
                    np.array(entity_name_embedding),
                    description,
                    np.array(description_embedding)
                )
                logger.info(f"Embedding stored for entity: {entity_name}")
                return description_embedding  # Return description embedding
            else:
                logger.warning(f"Failed to generate embedding for entity: {entity_name}. Not storing in PgVector.")
                return None
        except Exception as e:
            logger.error(f"Error embedding entity '{entity_name}': {e}")
            return None

    def remove_entity(self, entity_name: str) -> bool:
        """Removes an entity embedding from PgVector."""
        if not self.pgvector_client.is_connected():
            logger.error("PgVectorClient is not connected.")
            return False
        try:
            self.pgvector_client.delete_embedding(entity_name)
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
        if not self.pgvector_client.is_connected():
            logger.error("PgVectorClient is not connected.")
            return None
        try:
            name_embedding = self.embedder.get_embedding(entity_name)
            if name_embedding:
                similar_entities = self.pgvector_client.get_nearest_neighbors_by_entity_name(np.array(name_embedding), limit=limit)
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
        if not self.pgvector_client.is_connected():
            logger.error("PgVectorClient is not connected.")
            return None
        try:
            description_embedding = self.embedder.get_embedding(description)
            if description_embedding:
                similar_entities = self.pgvector_client.get_nearest_neighbors_by_description(np.array(description_embedding), limit=limit)
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
