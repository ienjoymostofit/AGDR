import logging
from typing import Dict, List, Optional

from core.models import Entity, KnowledgeGraph, Relationship
from clients.neo4j import Neo4jClient
from clients.openai import OpenAIClient
from services.embedder import Embedder  # Import Embedder

logger = logging.getLogger(__name__)

EXAMPLE_JSON_STR = """
{
    "entities": [
        {"id": "1", "name": "GlassWindow", "description": "A type of material used for windows that don't break when hit hard.", "category": ["Material"]},
        {"id": "2", "name": "Airbag", "description": "A safety device in vehicles that inflate to cushion impacts.", "category": ["Product"]},
        {"id": "3", "name": "ImpactResistantMaterial", "description": "A type of material that doesn't break when hit hard.", "category": ["Material"]},
        {"id": "4", "name": "Polycarbonate", "description": "A type of plastic used in various applications.", "category": ["Material"]},
        {"id": "5", "name": "CarbonFiberComposite", "description": "A material made from fibers and resin.", "category": ["Material"]},
        {"id": "6", "name": "ThermalEffect", "description": "The reaction of a material to heat and temperature changes.", "category": ["Property"]},
        {"id": "7", "name": "Rigidity", "description": "A measure of an object's resistance to deformation under stress.", "category": ["Property"]},
        {"id": "8", "name": "Durability", "description": "The ability of a material to withstand wear and tear over time.", "category": ["Property"]}
    ],
    "relationships": [
        {"source_entity_id": "3", "target_entity_id": "1", "relation_type": "example_of", "attributes": {"effectiveness": "high"}},
        {"source_entity_id": "3", "target_entity_id": "2", "relation_type": "example_of", "attributes": {"reliability": "high", "cost_effectiveness": "medium"}},
        {"source_entity_id": "6", "target_entity_id": "3", "relation_type": "characteristic_of", "attributes": {"importance": "critical", "measurability": "quantifiable"}},
        {"source_entity_id": "7", "target_entity_id": "3", "relation_type": "characteristic_of", "attributes": {"strength": "high", "flexibility": "low"}},
        {"source_entity_id": "8", "target_entity_id": "3", "relation_type": "characteristic_of", "attributes": {"lifespan": "years", "maintenance_needs": "low"}}
    ]
}
"""


class KnowledgeGraphGenerator:
    """Orchestrates the knowledge graph generation process."""

    def __init__(self, openai_client: OpenAIClient, neo4j_client: Neo4jClient, embedder: Embedder):
        """Initializes the KnowledgeGraphGenerator with the specified clients."""
        self.openai_client = openai_client
        self.neo4j_client = neo4j_client
        self.embedder = embedder
        self.similarity_threshold = 0.8 # "Gustav V" "King Gustav V" : 0.86 with granite-embedding:30m-en

    def generate_knowledge_graph_data(self, reasoning_trace: str, existing_entity_names_str: str = "") -> Optional[KnowledgeGraph]:
        """Generates structured knowledge graph data using OpenAI."""
        prompt = f"""Analyze the given content and extract all mentioned entities and relationships. Use singular MixedCase for entity names, and snake case names for relationships. Do not make up information, only refer to the content provided.

        <content>{reasoning_trace}</content>

        The following entities already exist in the knowledge graph: {existing_entity_names_str}.  Consider these existing entities when extracting new entities and relationships.

        Return a JSON object containing 'entities' and 'relationships' keys. The 'entities' key should contain an array of entities, each with 'id', 'name', 'description', and 'category' fields. The 'category' field should be a list of strings. The 'relationships' key should contain an array of relationships, each with 'source_entity_id', 'target_entity_id', 'relation_type', and 'attributes' fields.

            Example:
        {EXAMPLE_JSON_STR}
            """

        return self.openai_client.generate_structured_data(prompt)

    def run_kg_generation_iterations(self, initial_prompt: str, max_iterations: int):
        """Runs the knowledge graph generation process for a specified number of iterations."""
        knowledge_graph_data: Optional[KnowledgeGraph] = None

        existing_entity_names = self.neo4j_client.query_node_names()
        existing_entity_names_str = ", ".join(existing_entity_names)

        prompt = initial_prompt
        original_prompt = initial_prompt  # Keep original prompt for context in new prompt generation

        for i in range(max_iterations):
            logger.info(f"Starting iteration {i + 1}/{max_iterations}")

            if knowledge_graph_data:
                logger.info("Generating next iteration prompt...")
                prompt = self.openai_client.generate_prompt(knowledge_graph_data, original_prompt)
                if not prompt:
                    logger.error("Failed to generate new prompt, stopping iterations.")
                    break
                logger.info(f"Next prompt: {prompt}")

            reasoning_trace = self.openai_client.generate_reasoning_trace(prompt)
            if not reasoning_trace:
                logger.error("Failed to generate reasoning trace, stopping iterations.")
                break

            new_knowledge_graph_data = self.generate_knowledge_graph_data(reasoning_trace, existing_entity_names_str)

            if new_knowledge_graph_data and new_knowledge_graph_data.entities:
                logger.info(f"Found {len(new_knowledge_graph_data.entities)} new entities.")
                entity_id_map: Dict[str, str] = {}  # LLM entity ID (str) -> Neo4j Node ID (str)

                for entity in new_knowledge_graph_data.entities:
                    logger.info(f"Processing entity: {entity.name} (LLM ID: {entity.id})")

                    # Check for similar entities and potentially update the entity name
                    best_similarity = 0.0
                    most_similar_entity = None
                    for existing_entity_name in existing_entity_names:
                        similarity = self.embedder.compare_texts_cosine(entity.name, existing_entity_name)
                        if similarity == 1.0:
                            best_similarity = 1.0
                            most_similar_entity = existing_entity_name
                            break
                        elif similarity > best_similarity:
                            best_similarity = similarity
                            most_similar_entity = existing_entity_name

                    if best_similarity > self.similarity_threshold and best_similarity < 1.0:
                        logger.info(f"Entity '{entity.name}' is similar to existing entity '{most_similar_entity}' (Similarity: {best_similarity:.2f}). Updating name.")
                        entity.name = most_similar_entity  # Update the entity name

                    node_id = self.neo4j_client.create_node(entity)
                    if node_id:
                        entity_id_map[entity.id] = node_id
                        logger.info(f"Entity '{entity.name}', LLM ID {entity.id} -> Neo4j ID: {node_id}")
                        entity.id = node_id  # Update entity's ID to Neo4j ID
                    else:
                        logger.warning(f"Failed to create Neo4j node for entity '{entity.name}'. Skipping relationships for this entity.")

                logger.info(f"Current entity_id_map: {entity_id_map}")  # Debug logging

                # Process relationships using the ID mapping
                for relationship in new_knowledge_graph_data.relationships:
                    source_neo4j_id = entity_id_map.get(relationship.source_entity_id)
                    target_neo4j_id = entity_id_map.get(relationship.target_entity_id)

                    if source_neo4j_id and target_neo4j_id:
                        logger.info(
                            f"Mapping relationship: Source {relationship.source_entity_id}->{source_neo4j_id}, Target {relationship.target_entity_id}->{target_neo4j_id}"
                        )
                        relationship.source_entity_id = source_neo4j_id
                        relationship.target_entity_id = target_neo4j_id
                        self.neo4j_client.create_relationship(relationship)
                    else:
                        logger.warning(
                            f"Skipping relationship '{relationship.relation_type}' due to missing Neo4j IDs. "
                            f"Source ID {relationship.source_entity_id} -> {source_neo4j_id}, "
                            f"Target ID {relationship.target_entity_id} -> {target_neo4j_id}"
                        )

                knowledge_graph_data = new_knowledge_graph_data

                if knowledge_graph_data:
                    logger.info("\n--- Entities added in this iteration ---")
                    for entity in knowledge_graph_data.entities:
                        logger.info(f"  - Name: {entity.name}, ID: {entity.id}, Categories: {entity.category}")
                    logger.info("\n--- Relationships added in this iteration ---")
                    for relationship in knowledge_graph_data.relationships:
                        logger.info(
                            f"  - {relationship.relation_type} from {relationship.source_entity_id} to {relationship.target_entity_id}, Attributes: {relationship.attributes}"
                        )
            else:
                logger.info("No new entities generated in this iteration.")

        logger.info("Knowledge graph generation process completed.")
