import logging
from typing import Dict, Optional
from models import Entity, Relationship
from settings import Settings
from openai_client import OpenAIClient
from models import KnowledgeGraph
from neo4j_client import Neo4jClient
import json

EXAMPLE_JSON_STR = json.dumps({
    "entities": [
        {"id": "1", "name": "GlassWindow", "description": "A type of material used for windows that don't break when hit hard.", "category": ["Material"]},
        {"id": "2", "name": "Airbag", "description": "A safety device in vehicles that inflate to cushion impacts.", "category": ["Product"]},
        {"id": "3", "name": "ImpactResistantMaterial", "description": "A type of material that doesn't break when hit hard.", "category": ["Material"]},
        {"id": "4", "name": "Polycarbonate", "description": "A type of plastic used in various applications.", "category": ["Material"]},
        {"id": "5", "name": "CarbonFiberComposite", "description": "A material made from fibers and resin.", "category": ["Material"]},
        {"id": "6", "name": "ThermalEffect", "description": "The reaction of a material to heat and temperature changes.", "category": ["Property"]},
        {"id": "7", "name": "Rigidity", "description": "A measure of an object's resistance to deformation under stress.", "category": ["Property"]},
        {"id": "8", "name": "Durability", "description": "The ability of a material to withstand wear and tear over time.", "category": ["Property"]},
        {"id": "9", "name": "ThermalInsulation", "description": "A property that prevents the transfer of heat through materials.", "category": ["Property"]}
    ],
    "relationships": [
        {"source_entity_id": "3", "target_entity_id": "1", "relation_type": "example_of", "attributes": {"effectiveness": "high"}},
        {"source_entity_id": "3", "target_entity_id": "2", "relation_type": "example_of", "attributes": {"reliability": "high", "cost_effectiveness": "medium"}},
        {"source_entity_id": "6", "target_entity_id": "3", "relation_type": "characteristic_of", "attributes": {"importance": "critical", "measurability": "quantifiable"}},
        {"source_entity_id": "7", "target_entity_id": "3", "relation_type": "characteristic_of", "attributes": {"strength": "high", "flexibility": "low"}},
        {"source_entity_id": "8", "target_entity_id": "3", "relation_type": "characteristic_of", "attributes": {"lifespan": "years", "maintenance_needs": "low"}},
        {"source_entity_id": "6", "target_entity_id": "9", "relation_type": "related_to", "attributes": {"correlation": "strong", "dependency": "direct"}},
        {"source_entity_id": "4", "target_entity_id": "1", "relation_type": "instance_of", "attributes": {"quality": "high", "cost": "moderate"}},
        {"source_entity_id": "5", "target_entity_id": "2", "relation_type": "instance_of", "attributes": {"strength_rating": "excellent", "weight": "light"}}
    ]
}, indent=2)

class KnowledgeGraphGenerator:
    """Orchestrates the knowledge graph generation process."""

    def __init__(self, openai_client: OpenAIClient, neo4j_client: Neo4jClient, settings: Settings):
        self.logger = logging.getLogger(__name__)

        self.openai_client = openai_client
        self.neo4j_client = neo4j_client
        self.settings = settings

    def generate_knowledge_graph_data(self, reasoning_trace: str, existing_entity_names_str: str = "") -> Optional[KnowledgeGraph]:
        """Generates structured knowledge graph data using OpenAI."""
        prompt = f"""Analyze the given content and extract all mentioned entities and relationships. Use singular MixedCase for entity names, and snake case names for relationships. Do not make up information, only refer to the content provided.

        <content>{reasoning_trace}</content>

        The following entities already exist in the knowledge graph: {existing_entity_names_str}.  Consider these existing entities when extracting new entities and relationships.

        Return a JSON object containing 'entities' and 'relationships' keys. The 'entities' key should contain an array of entities, each with 'id', 'name', 'description', and 'category' fields. The 'category' field should be a list of strings. The 'relationships' key should contain an array of relationships, each with 'source_entity_id', 'target_entity_id', 'relation_type', and 'attributes' fields.

            Example:
        {EXAMPLE_JSON_STR}
            """ # Using EXAMPLE_JSON_STR constant

        return self.openai_client.generate_structured_data(self.settings.entity_extraction_model_config, prompt) # Pass model config


    def run_kg_generation_iterations(self, initial_prompt: str, max_iterations: int):
        """Runs the knowledge graph generation process for a specified number of iterations."""
        knowledge_graph_data: Optional[KnowledgeGraph] = None

        existing_entity_names = self.neo4j_client.query_node_names()
        existing_entity_names_str = ", ".join(existing_entity_names)

        prompt = initial_prompt
        original_prompt = initial_prompt  # Keep original prompt for context in new prompt generation

        for _ in range(max_iterations):
            if knowledge_graph_data:
                self.logger.info("Generating next iteration prompt...")
                prompt = self.openai_client.generate_prompt(
                    self.settings.entity_extraction_model_config, knowledge_graph_data, original_prompt
                )
                if not prompt:
                    self.logger.error("Failed to generate new prompt, stopping iterations.")
                    break
                self.logger.info(f"Next prompt: {prompt}")

            reasoning_trace = self.openai_client.generate_reasoning_trace(self.settings.reasoning_model_config, prompt)
            if not reasoning_trace:
                self.logger.error("Failed to generate reasoning trace, stopping iterations.")
                break

            new_knowledge_graph_data = self.generate_knowledge_graph_data(reasoning_trace, existing_entity_names_str)

            if new_knowledge_graph_data and new_knowledge_graph_data.entities:
                self.logger.info(f"Found {len(new_knowledge_graph_data.entities)} new entities.")
                entity_id_map: Dict[int, str] = {} # LLM entity ID (int) -> Neo4j Node ID (str)

                entity_id_map = {}
                for entity_data in new_knowledge_graph_data.entities:
                    # Ensure we have an Entity object
                    entity = entity_data if isinstance(entity_data, Entity) else Entity(**entity_data)
                    original_entity_id = int(entity.id)  # Store original ID before it gets updated
                    self.logger.info(f"Processing entity: {entity.name} (Original LLM ID: {original_entity_id})")

                    node_id = self.neo4j_client.create_node(entity)
                    if node_id:
                        entity_id_map[original_entity_id] = node_id
                        self.logger.info(f"Entity '{entity.name}', Original ID {original_entity_id} -> Neo4j ID: {node_id}")
                        # Update entity's ID to Neo4j ID for subsequent iterations
                        entity.id = node_id
                    else:
                        self.logger.warning(f"Failed to create Neo4j node for entity '{entity.name}'. Skipping relationships for this entity.")
                        continue

                self.logger.info(f"Current entity_id_map: {entity_id_map}")  # Debug logging

                # Process relationships using the ID mapping
                for relationship_data in new_knowledge_graph_data.relationships:
                    relationship = relationship_data if isinstance(relationship_data, Relationship) else Relationship(**relationship_data)
                    original_source_id = int(relationship.source_entity_id)
                    original_target_id = int(relationship.target_entity_id)

                    source_neo4j_id = entity_id_map.get(original_source_id)
                    target_neo4j_id = entity_id_map.get(original_target_id)

                    if source_neo4j_id and target_neo4j_id:
                        self.logger.info(f"Mapping relationship: Source {original_source_id}->{source_neo4j_id}, Target {original_target_id}->{target_neo4j_id}")
                        relationship.source_entity_id = source_neo4j_id
                        relationship.target_entity_id = target_neo4j_id
                        self.neo4j_client.create_relationship(relationship)
                    else:
                        self.logger.warning(
                            f"Skipping relationship '{relationship.relation_type}' due to missing Neo4j IDs. "
                            f"Source ID {original_source_id} -> {source_neo4j_id}, "
                            f"Target ID {original_target_id} -> {target_neo4j_id}"
                        )

                knowledge_graph_data = new_knowledge_graph_data

                if knowledge_graph_data:
                    self.logger.info("\n--- Entities added in this iteration ---")
                    for entity in knowledge_graph_data.entities:
                        self.logger.info(f"  - Name: {entity.name}, ID: {entity.id}, Categories: {entity.category}")
                    self.logger.info("\n--- Relationships added in this iteration ---")
                    for relationship in knowledge_graph_data.relationships:
                        self.logger.info(f"  - {relationship.relation_type} from {relationship.source_entity_id} to {relationship.target_entity_id}, Attributes: {relationship.attributes}")

            else:
                self.logger.info("No new entities generated in this iteration.")

            # Stop iterations if no new entities are generated?

        self.logger.info("Knowledge graph generation process completed.")
