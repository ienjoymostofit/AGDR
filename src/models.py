from typing import List, Dict, Any
from pydantic import BaseModel

class Entity(BaseModel):
    """
    Represents an entity in the knowledge graph.

    Attributes:
        id (str): Unique identifier for the entity.
        name (str): Name of the entity.
        description (str): Description of the entity.
        category (List[str]): List of categories the entity belongs to.
    """
    id: str
    name: str
    description: str
    category: List[str]

class Relationship(BaseModel):
    """
    Represents a relationship between two entities in the knowledge graph.

    Attributes:
        source_entity_id (str): ID of the source entity.
        target_entity_id (str): ID of the target entity.
        relation_type (str): Type of relationship between the entities (snake_case).
        attributes (Dict[str, Any]):  Attributes describing the relationship.
    """
    source_entity_id: str
    target_entity_id: str
    relation_type: str
    attributes: Dict[str, Any]


class KnowledgeGraph(BaseModel):
    """
    Represents a collection of entities and relationships forming a knowledge graph.

    Attributes:
        entities (List[Entity]): List of entities in the knowledge graph.
        relationships (List[Relationship]): List of relationships in the knowledge graph.
    """
    entities: List[Entity]
    relationships: List[Relationship]

    def to_dict(self) -> Dict:
        """
        Converts the KnowledgeGraphData object to a dictionary.

        Returns:
            Dict: A dictionary representation of the KnowledgeGraphData, suitable for JSON serialization.
        """
        return self.model_dump()
