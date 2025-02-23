from typing import List, Dict, Any
from pydantic import BaseModel, Field

class Entity(BaseModel):
    """Represents an entity in the knowledge graph."""

    id: str = Field(str, description="Unique identifier for the entity.")
    name: str = Field(..., description="Name of the entity.")
    description: str = Field(..., description="Description of the entity.")
    category: List[str] = Field(..., description="List of categories the entity belongs to.")


class Relationship(BaseModel):
    """Represents a relationship between two entities in the knowledge graph."""

    source_entity_id: str = Field(..., description="ID of the source entity.")
    target_entity_id: str = Field(..., description="ID of the target entity.")
    relation_type: str = Field(..., description="Type of relationship between the entities (snake_case).")
    attributes: Dict[str, Any] = Field(..., description="Attributes describing the relationship.")


class KnowledgeGraph(BaseModel):
    """Represents a collection of entities and relationships forming a knowledge graph."""

    entities: List[Entity] = Field(..., description="List of entities in the knowledge graph.")
    relationships: List[Relationship] = Field(..., description="List of relationships in the knowledge graph.")

    def to_dict(self) -> Dict:
        """Converts the KnowledgeGraphData object to a dictionary."""
        return self.model_dump()
