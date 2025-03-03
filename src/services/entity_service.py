import logging
from typing import Any, List, Tuple, Optional

from core.interfaces import GraphDatabase
from services.embed_service import EmbedService
from core.models import Entity, KnowledgeGraph, Relationship

logger = logging.getLogger(__name__)

class EntityService:
    """
    Service for managing entities, including embedding, similarity search, and storage in Neo4j and PgVector.
    """

    def __init__(self, embed_service: EmbedService, graph_db: GraphDatabase):
        """
        Initializes the EntityService with EmbedService and GraphDatabase instances.
        """
        self.embed_service = embed_service
        self.graph_db = graph_db

    def update_entity(self, old_name:str, new_name: str, description: str):
        """Updates an entity description and stores it using EmbedService."""
        self.embed_service.embed_entity(new_name, description)
        self.graph_db.update_node_name_and_description(old_name, new_name, description)

    def embed_entity(self, entity_name: str, description: str):
        """Embeds an entity description and stores it using EmbedService."""
        self.embed_service.embed_entity(entity_name, description)

    def get_entity_subgraph(self, entity_name: str, depth: int = 1) -> KnowledgeGraph:
        """Retrieves the subgraph of an entity from the graph database."""
        entries = self.graph_db.get_subgraph(entity_name, depth)

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
        """Finds similar entities using EmbedService."""
        return self.embed_service.find_similar_entities_by_entity_name(entity_name, limit)

    def find_similar_entities_by_description(self, entity_name:str, description: str, limit: int = 5) -> Optional[List[Tuple[str, str, float]]]:
        """Finds similar entities using EmbedService."""
        return self.embed_service.find_similar_entities_by_description(entity_name, description, limit)

    def create_entity_node(self, entity: Entity) -> Optional[str]:
        """Creates an entity node in the graph database."""
        return self.graph_db.create_node(entity)

    def get_entity_by_name(self, entity_name: str) -> Optional[Entity]:
        """Retrieves an entity by name from the graph database."""
        return self.graph_db.get_node_by_name(entity_name)

    def get_entity_names(self) -> List[str]:
        """Retrieves entity names from the graph database."""
        return self.graph_db.query_node_names()

    def create_relationship(self, relationship_data: Any) -> Optional[str]:
        """Creates a relationship in the graph database."""
        return self.graph_db.create_relationship(relationship_data)

    def find_longest_shortest_paths(self) -> List[Any]|None:
        """Retrieves the longest shortest paths from the graph database."""
        return self.graph_db.find_longest_shortest_paths()
