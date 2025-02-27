import logging
from typing import Any, List, Tuple, Optional

from clients.neo4j import Neo4jClient
from services.pgvector_service import PgVectorService
from services.embedder import Embedder
from core.models import Entity

logger = logging.getLogger(__name__)

class EntityService:
    """
    Service for managing entities, including embedding, similarity search, and storage in Neo4j and PgVector.
    """

    def __init__(self, pgvector_service: PgVectorService, neo4j_client: Neo4jClient, embedder: Embedder):
        """
        Initializes the EntityService with PgVectorService and Neo4jClient instances.
        """
        self.pgvector_service = pgvector_service
        self.neo4j_client = neo4j_client
        self.embedder = embedder # Still using embedder directly for is_same_concept for now

    def embed_entity(self, entity_name: str, description: str):
        """Embeds an entity description and stores it using PgVectorService."""
        self.pgvector_service.embed_entity(entity_name, description)

    def find_similar_entities(self, entity_name: str, description: str, limit: int = 5) -> Optional[List[Tuple[str, str, float]]]:
        """Finds similar entities using PgVectorService."""
        return self.pgvector_service.find_similar_entities(entity_name, description, limit)

    def create_entity_node(self, entity: Entity) -> Optional[str]:
        """Creates an entity node in Neo4j using Neo4jClient."""
        return self.neo4j_client.create_node(entity)

    def get_entity_names(self) -> List[str]:
        """Retrieves entity names from Neo4j using Neo4jClient."""
        return self.neo4j_client.query_node_names()

    def create_relationship(self, relationship_data: Any) -> Optional[str]:
        """Creates a relationship in Neo4j using Neo4jClient."""
        return self.neo4j_client.create_relationship(relationship_data)

    def find_longest_shortest_paths(self) -> List[Any]|None:
        """Retrieves the longest shortest paths from Neo4j using Neo4jClient."""
        return self.neo4j_client.find_longest_shortest_paths()

    def is_same_concept(self, text1: str, text2: str) -> bool:
        """
        Determines if two texts represent the same concept using cosine similarity of embeddings.
        Uses a threshold of 0.95 for similarity.
        """
        embedding1 = self.embedder.get_embedding(text1)
        embedding2 = self.embedder.get_embedding(text2)

        if embedding1 is None or embedding2 is None:
            logger.warning("Could not generate embeddings for comparison.")
            return False

        similarity = self.embedder.cosine_similarity(embedding1, embedding2)
        logger.debug(f"Cosine similarity between '{text1}' and '{text2}': {similarity}")
        return similarity >= 0.95
