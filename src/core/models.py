from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class Entity(BaseModel):
    """Represents an entity in the knowledge graph."""

    id: Optional[str] = Field(default=None, description="Unique identifier for the entity.")
    name: str = Field(default="Unknown", description="Name of the entity.")
    description: str = Field(default="", description="Description of the entity.")
    category: List[str] = Field(default_factory=list, description="List of categories the entity belongs to.")

    class Config:
        extra = "ignore"


class Relationship(BaseModel):
    """Represents a relationship between two entities in the knowledge graph."""

    source_entity_name: str = Field(default="Unknown", description="Name of the source entity.")
    target_entity_name: str = Field(default="Unknown", description="Name of the target entity.")
    relation_type: str = Field(default="unclassified", description="Type of relationship between the entities (snake_case).")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Attributes describing the relationship.")

    class Config:
        extra = "ignore"


class KnowledgeGraph(BaseModel):
    """Represents a collection of entities and relationships forming a knowledge graph."""

    entities: List[Entity] = Field(default_factory=list, description="List of entities in the knowledge graph.")
    relationships: List[Relationship] = Field(default_factory=list, description="List of relationships in the knowledge graph.")

    class Config:
        extra = "ignore"

    def get_entity(self, entity_name: str) -> Optional[Entity]:
        """Checks if the knowledge graph contains an entity with the given name."""
        return next((entity for entity in self.entities if entity.name == entity_name), None)

    def get_relationships(self, source_entity_name: str, target_entity_name: str) -> List[Relationship]:
        """Returns a list of relationships between the given entities."""
        return [rel for rel in self.relationships if rel.source_entity_name == source_entity_name and rel.target_entity_name == target_entity_name]

    def to_dict(self) -> Dict:
        """Converts the KnowledgeGraphData object to a dictionary."""
        return self.model_dump()


class ConflictResolutionResult(BaseModel):
    reasoning: Optional[str]
    action: Optional[str]
    new_name: Optional[str]
    new_description: Optional[str]
