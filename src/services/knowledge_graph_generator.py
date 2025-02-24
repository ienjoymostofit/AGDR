import logging
from typing import Dict, List, Optional
import numpy as np
from core.models import Entity, KnowledgeGraph, Relationship
from clients.neo4j import Neo4jClient
from clients.openai import OpenAIClient
from services.embedder import Embedder  # Import Embedder
import random

logger = logging.getLogger(__name__)

EXAMPLE_JSON_STR = """
{
    "entities": [
        {"name": "GlassWindow", "description": "A type of material used for windows that don't break when hit hard.", "category": ["Material"]},
        {"name": "Airbag", "description": "A safety device in vehicles that inflate to cushion impacts.", "category": ["Product"]},
        {"name": "ImpactResistantMaterial", "description": "A type of material that doesn't break when hit hard.", "category": ["Material"]},
        {"name": "Polycarbonate", "description": "A type of plastic used in various applications.", "category": ["Material"]},
        {"name": "CarbonFiberComposite", "description": "A material made from fibers and resin.", "category": ["Material"]},
        {"name": "ThermalEffect", "description": "The reaction of a material to heat and temperature changes.", "category": ["Property"]},
        {"name": "Rigidity", "description": "A measure of an object's resistance to deformation under stress.", "category": ["Property"]},
        {"name": "Durability", "description": "The ability of a material to withstand wear and tear over time.", "category": ["Property"]}
    ],
    "relationships": [
        {"source_entity_name": "ImpactResistantMaterial", "target_entity_name": "GlassWindow", "relation_type": "example_of", "attributes": {"effectiveness": "high"}},
        {"source_entity_name": "ImpactResistantMaterial", "target_entity_name": "Airbag", "relation_type": "example_of", "attributes": {"reliability": "high", "cost_effectiveness": "medium"}},
        {"source_entity_name": "ThermalEffect", "target_entity_name": "ImpactResistantMaterial", "relation_type": "characteristic_of", "attributes": {"importance": "critical", "measurability": "quantifiable"}},
        {"source_entity_name": "Rigidity", "target_entity_name": "ImpactResistantMaterial", "relation_type": "characteristic_of", "attributes": {"strength": "high", "flexibility": "low"}},
        {"source_entity_name": "Durability", "target_entity_name": "ImpactResistantMaterial", "relation_type": "characteristic_of", "attributes": {"lifespan": "years", "maintenance_needs": "low"}}
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

    def generate_knowledge_graph_data(self, reasoning_trace: str, existing_entity_names_str: str = "") -> Optional[KnowledgeGraph]:
        # The following entities already exist in the knowledge graph: {existing_entity_names_str}.  Consider these existing entities when extracting new entities and relationships.
        """Generates structured knowledge graph data using OpenAI."""
        prompt = f"""Analyze the given content and extract all mentioned entities and relationships. Use singular MixedCase for entity names, and snake case names for relationships. Do not make up information, only refer to the content provided, and make sure to capture all entities and relationships mentioned in the reasoning trace.

        <content>{reasoning_trace}</content>


        Return a JSON object containing 'entities' and 'relationships' keys. The 'entities' key should contain an array of entities, each with 'name', 'description', and 'category' fields. The 'category' field should be a list of strings. The 'relationships' key should contain an array of relationships, each with 'source_entity_name', 'target_entity_name', 'relation_type', and 'attributes' fields.

            Example:
        {EXAMPLE_JSON_STR}
            """

        return self.openai_client.generate_structured_data(prompt)

    def run_kg_generation_iterations(self, initial_prompt: str, max_iterations: int):
        """Runs the knowledge graph generation process for a specified number of iterations."""
        knowledge_graph_data: Optional[KnowledgeGraph] = None

        prompt = initial_prompt
        # original_prompt = initial_prompt  # Keep original prompt for context in new prompt generation
        previous_node_name = None
        for i in range(max_iterations):
            logger.info(f"Starting iteration {i + 1}/{max_iterations}")

            ls_paths = self.neo4j_client.find_longest_shortest_paths()
            print(f"Longest Shortest paths: {ls_paths}")
            # Pick a random path from the longest paths
            if ls_paths and len(ls_paths) > 0:
                path = random.choice(ls_paths)
                start_node_name = path["endNodeName"]
                start_node_description = path["endNodeDescription"]
                if previous_node_name == start_node_name:
                    start_node_name = path["startNodeName"]
                    start_node_description = path["startNodeDescription"]
                previous_node_name = start_node_name
                prompt = f"Given the concept of '{start_node_name} ({start_node_description})', what related concepts and relationships can be explored to expand our knowledge graph?"
                logger.info(f"Generated prompt: {prompt}")

            reasoning_trace = self.openai_client.generate_reasoning_trace(prompt)
            if not reasoning_trace:
                logger.error("Failed to generate reasoning trace, stopping iterations.")
                break

            existing_entity_names = self.neo4j_client.query_node_names()
            existing_entity_names_str = ", ".join(existing_entity_names)

            new_knowledge_graph_data = self.generate_knowledge_graph_data(reasoning_trace, existing_entity_names_str)

            if new_knowledge_graph_data and new_knowledge_graph_data.entities:
                logger.info(f"Found {len(new_knowledge_graph_data.entities)} new entities.")

                for entity in new_knowledge_graph_data.entities:
                    logger.info(f"Processing entity: {entity.name}")

                    # Check for similar entities and potentially update the entity name
                    same_concept_entity = None
                    for existing_entity_name in existing_entity_names:
                        same_concept = self.embedder.is_same_concept(entity.name, existing_entity_name)
                        if same_concept:
                            # TODO: There are cases where the descriptions are completely different,
                            # but the names are very similar. Need to handle this somehow..
                            # Match on the name for now
                            same_concept_entity = existing_entity_name
                            break

                    if same_concept_entity:
                        logger.info(f"Entity '{entity.name}' is similar to existing entity '{same_concept_entity}' Updating name.")
                        entity.name = same_concept_entity  # Update the entity name

                    node_id = self.neo4j_client.create_node(entity)
                    if node_id:
                        entity.id = node_id
                        logger.info(f"Entity '{entity.name}', Neo4j ID: {node_id}")
                    else:
                        logger.warning(f"Failed to create Neo4j node for entity '{entity.name}'. Skipping relationships for this entity.")

                # Process relationships using the ID mapping
                for relationship in new_knowledge_graph_data.relationships:
                    logger.info(
                        f"Mapping relationship: Source {relationship.source_entity_name}, Target {relationship.target_entity_name}"
                    )
                    self.neo4j_client.create_relationship(relationship)

                knowledge_graph_data = new_knowledge_graph_data

                if knowledge_graph_data:
                    logger.info("\n--- Entities added in this iteration ---")
                    for entity in knowledge_graph_data.entities:
                        logger.info(f"  - Name: {entity.name}, ID: {entity.id}, Categories: {entity.category}")
                    logger.info("\n--- Relationships added in this iteration ---")
                    for relationship in knowledge_graph_data.relationships:
                        logger.info(
                            f"  - {relationship.relation_type} from {relationship.source_entity_name} to {relationship.target_entity_name}, Attributes: {relationship.attributes}"
                        )
            else:
                logger.info("No new entities generated in this iteration.")

        logger.info("Knowledge graph generation process completed.")
