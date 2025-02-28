import logging
from typing import Any, List, Tuple, Optional

from clients.neo4j import Neo4jClient
from services.embed_service import EmbedService
from core.models import Entity, KnowledgeGraph, Relationship

logger = logging.getLogger(__name__)

class EntityService:
    """
    Service for managing entities, including embedding, similarity search, and storage in Neo4j and PgVector.
    """

    def __init__(self, pgvector_service: EmbedService, neo4j_client: Neo4jClient):
        """
        Initializes the EntityService with PgVectorService and Neo4jClient instances.
        """
        self.pgvector_service = pgvector_service
        self.neo4j_client = neo4j_client

    def update_entity(self, old_name:str, new_name: str, description: str):
        """Updates an entity description and stores it using PgVectorService."""
        self.pgvector_service.embed_entity(new_name, description)
        self.neo4j_client.update_node_name_and_description(old_name, new_name, description)

    def embed_entity(self, entity_name: str, description: str):
        """Embeds an entity description and stores it using PgVectorService."""
        self.pgvector_service.embed_entity(entity_name, description)

    def get_entity_subgraph(self, entity_name: str, depth: int = 1) -> KnowledgeGraph:
        """Retrieves the subgraph of an entity from Neo4j using Neo4jClient."""
        entries = self.neo4j_client.get_subgraph(entity_name, depth)

        graph = KnowledgeGraph(entities=[], relationships=[])
        for entry in entries:
            try:
                # Extract nodes and relationship from the entry
                n = entry["n"]
                m = entry["m"]
                relationships = entry["r"]

                # Create or retrieve the source entity
                source = graph.get_entity(n["name"])
                if source is None:
                    source = Entity(
                        id=n.element_id,
                        name=n["name"],
                        description=n["description"],
                        category=list(n.labels)
                    )
                    graph.entities.append(source)

                # Create or retrieve the target entity
                target = graph.get_entity(m["name"])
                if target is None:
                    target = Entity(
                        id=m.element_id,
                        name=m["name"],
                        description=m["description"],
                        category=list(m.labels)
                    )
                    graph.entities.append(target)

                # Create the relationships
                for r in relationships:
                    relationship = Relationship(
                        source_entity_name=source.name,
                        target_entity_name=target.name,
                        relation_type=r.type,
                        attributes=r.get("properties", {})
                    )
                    graph.relationships.append(relationship)
            except Exception as e:
                logger.error(f"Error parsing entry: {entry}, Exception: {e}")

        return graph

    def find_similar_entities_by_name(self, entity_name: str, limit: int = 5) -> Optional[List[Tuple[str, str, float]]]:
        """Finds similar entities using PgVectorService."""
        return self.pgvector_service.find_similar_entities_by_entity_name(entity_name, limit)

    def find_similar_entities_by_description(self, entity_name:str, description: str, limit: int = 5) -> Optional[List[Tuple[str, str, float]]]:
        """Finds similar entities using PgVectorService."""
        return self.pgvector_service.find_similar_entities_by_description(entity_name, description, limit)

    def create_entity_node(self, entity: Entity) -> Optional[str]:
        """Creates an entity node in Neo4j using Neo4jClient."""
        return self.neo4j_client.create_node(entity)

    def get_entity_by_name(self, entity_name: str) -> Optional[Entity]:
        """Retrieves an entity by name from Neo4j using Neo4jClient."""
        return self.neo4j_client.get_node_by_name(entity_name)

    def get_entity_names(self) -> List[str]:
        """Retrieves entity names from Neo4j using Neo4jClient."""
        return self.neo4j_client.query_node_names()

    def create_relationship(self, relationship_data: Any) -> Optional[str]:
        """Creates a relationship in Neo4j using Neo4jClient."""
        return self.neo4j_client.create_relationship(relationship_data)

    def find_longest_shortest_paths(self) -> List[Any]|None:
        """Retrieves the longest shortest paths from Neo4j using Neo4jClient."""
        return self.neo4j_client.find_longest_shortest_paths()
