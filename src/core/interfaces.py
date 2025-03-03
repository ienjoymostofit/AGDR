from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple, Dict

from core.models import Entity, Relationship, ConflictResolutionResult, KnowledgeGraph


class GraphDatabase(ABC):
    """Interface for graph database operations."""

    @abstractmethod
    def close(self) -> None:
        """Closes the database connection."""
        pass

    @abstractmethod
    def verify_connection(self) -> None:
        """Verifies the connection to the database."""
        pass

    @abstractmethod
    def update_node_name_and_description(self, old_name: str, new_name: str, description: str) -> None:
        """Updates the name and description of a node in the database."""
        pass

    @abstractmethod
    def get_node_by_name(self, name: str) -> Optional[Entity]:
        """Retrieves a node from the database by its name."""
        pass

    @abstractmethod
    def query_node_names(self) -> List[str]:
        """Queries the database for all node names."""
        pass

    @abstractmethod
    def get_subgraph(self, node_name: str, depth: int = 1) -> Any:
        """Queries for a subgraph around a given node name up to a certain depth."""
        pass

    @abstractmethod
    def create_node(self, entity: Entity) -> Optional[str]:
        """Creates a node in the database for the given entity."""
        pass

    @abstractmethod
    def create_relationship(self, relationship: Relationship) -> None:
        """Creates a relationship in the database."""
        pass

    @abstractmethod
    def find_longest_shortest_paths(self) -> List[Tuple[str, str, int]] | None:
        """Finds the longest shortest paths in the graph."""
        pass

    @abstractmethod
    def find_longest_paths(self) -> List[str]:
        """Finds the longest path in the graph and returns a list of node IDs."""
        pass


class VectorDatabase(ABC):
    """Interface for vector database operations."""

    @abstractmethod
    def connect(self) -> None:
        """Establishes a connection to the database."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Closes the database connection."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if the database connection is established."""
        pass

    @abstractmethod
    def create_extension(self) -> None:
        """Creates the vector extension in the database if it doesn't exist."""
        pass

    @abstractmethod
    def create_table(self) -> None:
        """Creates the embeddings table if it doesn't exist."""
        pass

    @abstractmethod
    def get_entities_from_last_id(self, last_id: int, limit: int) -> Optional[List[Entity]]:
        """Retrieves entities from the table starting from the last_id."""
        pass

    @abstractmethod
    def delete_embedding(self, entity_name: str) -> None:
        """Deletes an embedding for an entity from the database."""
        pass

    @abstractmethod
    def insert_embedding(self, entity_name: str, entity_name_embedding: Any,
                         description: str, description_embedding: Any) -> None:
        """Inserts an embedding for an entity into the database."""
        pass

    @abstractmethod
    def get_nearest_neighbors_by_entity_name(self, entity_name_embedding: Any,
                                            limit: int = 5) -> Optional[List[Tuple[str, str, float]]]:
        """Retrieves the nearest neighbors to a given entity_name."""
        pass

    @abstractmethod
    def get_nearest_neighbors_by_description(self, embedding: Any,
                                            limit: int = 5) -> Optional[List[Tuple[str, str, float]]]:
        """Retrieves the nearest neighbors to a given embedding vector."""
        pass


class LLMClient(ABC):
    """Interface for language model operations."""

    @abstractmethod
    def generate_reasoning_trace(self, prompt: str) -> Optional[str]:
        """Generates a reasoning trace from the specified language model."""
        pass

    @abstractmethod
    def extract_knowledge_graph(self, prompt: str) -> Optional[Any]:
        """Generates structured knowledge graph data."""
        pass

    @abstractmethod
    def conflict_resolution(self, prompt: str) -> Optional[Any]:
        """Resolves conflicts between entities."""
        pass


class EmbeddingProvider(ABC):
    """Interface for embedding operations."""

    @abstractmethod
    def get_embedding(self, text: str) -> Any:
        """Gets the embedding for the given text."""
        pass

    @abstractmethod
    def is_same_concept(self, text1: str, text2: str) -> bool:
        """Determines if two texts refer to the same concept."""
        pass

    @abstractmethod
    def compare_texts_cosine(self, text1: str, text2: str) -> float:
        """Compares two texts using cosine similarity."""
        pass

class ConflictResolver(ABC):
    """Interface for conflict resolution operations."""

    @abstractmethod
    def resolve_entity_conflict(self, existing_entity: Entity, new_entity: Entity,
                                context: Optional[Dict[str, Any]] = None) -> ConflictResolutionResult:
        """
        Resolves a conflict between an existing entity and a new entity.

        Args:
            existing_entity: The entity that already exists in the knowledge graph
            new_entity: The new entity being added to the knowledge graph
            context: Optional additional context information

        Returns:
            A ConflictResolutionResult containing the resolution decision and any updated entity information
        """
        pass

class KnowledgeExtractor(ABC):
    """Interface for extracting knowledge graphs from text."""

    @abstractmethod
    def extract_knowledge_graph(self, text: str) -> Optional[KnowledgeGraph]:
        """
        Extracts a knowledge graph from the provided text.

        Args:
            text: The text to extract knowledge from

        Returns:
            A KnowledgeGraph object containing entities and relationships
        """
        pass

class GraphPopulator(ABC):
    """Interface for populating the knowledge graph with entities and relationships."""

    @abstractmethod
    def add_entity(self, entity: Entity) -> Optional[str]:
        """
        Adds an entity to the knowledge graph, handling potential conflicts.

        Args:
            entity: The entity to add

        Returns:
            The entity ID if successfully added, None otherwise
        """
        pass

    @abstractmethod
    def add_relationship(self, relationship: Relationship) -> bool:
        """
        Adds a relationship to the knowledge graph.

        Args:
            relationship: The relationship to add

        Returns:
            True if successfully added, False otherwise
        """
        pass

    @abstractmethod
    def merge_knowledge_graph(self, knowledge_graph: KnowledgeGraph) -> KnowledgeGraph:
        """
        Merges a knowledge graph into the existing graph.

        Args:
            knowledge_graph: The knowledge graph to merge

        Returns:
            The merged knowledge graph
        """
        pass

class ReasoningService(ABC):
    """Interface for generating reasoning traces."""

    @abstractmethod
    def generate_reasoning_trace(self, prompt: str) -> Optional[str]:
        """
        Generates a reasoning trace from the given prompt.

        Args:
            prompt: The prompt to reason about

        Returns:
            The generated reasoning trace as text
        """
        pass
