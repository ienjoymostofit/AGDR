import logging
from clients.openai import OpenAIClient
import random
from services.entity_service import EntityService
from typing import Optional
from core.models import Entity, KnowledgeGraph
import sys
import os
import json

logger = logging.getLogger(__name__)



class KnowledgeGraphGenerator:
    """Orchestrates the knowledge graph generation process."""

    def __init__(self, openai_client: OpenAIClient, entity_service: EntityService):
        """Initializes the KnowledgeGraphGenerator with OpenAIClient and EntityService."""
        self.openai_client = openai_client
        self.entity_service = entity_service

    def generate_knowledge_graph_data(self, reasoning_trace: str) -> Optional[KnowledgeGraph]:
        # The following entities already exist in the knowledge graph: {existing_entity_names_str}.  Consider these existing entities when extracting new entities and relationships.
        """Generates structured knowledge graph data using OpenAI."""
        # Read prompt from prompts/extract_entities_and_relationships.md
        with open(os.path.join(sys.path[0], "prompts/extract_entities_and_relationships.md"), "r") as f:
            prompt = f.read()
        prompt += f"\n<content>\n{reasoning_trace}\n</content>\n"

        return self.openai_client.extract_knowledge_graph(prompt)

    def resolve_entity_insertion_conflict(self, knowledge_graph_data: KnowledgeGraph, existing_entity: Entity, new_entity: Entity):
        """Resolves entity conflict by updating the entity name and relationships."""

        concept_a = existing_entity.name
        concept_b = new_entity.name

        entity_a = existing_entity
        entity_b = new_entity

        concept_a_subgraph = self.entity_service.get_entity_subgraph(concept_a, 1);

        if concept_a_subgraph.entities:
            concept_a_subgraph_prompt = f"**Subgraph:**\n ```json\n {json.dumps(concept_a_subgraph.to_dict(), indent=2)}\n```"
        else:
            concept_a_subgraph_prompt = ""

        prompt = f"""
        You are building a knowledge graph, and you have encountered a potential conflict between two concepts when adding a newly discovered entity.

        When building a knowledge graph, it is essential to ensure that the concepts are distinct and do not overlap.

        Given the two concepts below, your task is to determine if they are the same, or different concepts.

        ## Concept A (Existing):
        **Name:** {concept_a}
        **Description:** {entity_a.description}
        {concept_a_subgraph_prompt}

        ## Concept B (New):
        **Name:** {concept_b}
        **Description:** {entity_b.description}

        # Response format:
        {{
            "reasoning": "Explanation of the reasoning behind the action",
            "action": "same" | "distinct" | "merge",
            "new_name": "New Name", # Required if action is "merge" and optional if action is "distinct"
            "new_description": "New Description" # Required if action is "merge"
        }}

        # Guidelines:
        - Evaluate the concepts based on their name, description, and any relationships provided.
        - Determine if the concepts are the same, distinct, or related.
        - If the concepts are the same, respond with action set to "same".
        - If the concepts are distinct, respond with action set to "distinct", with a suggested new_name and new_description if applicable.
        - If the concepts are related and should be combined, respond with action set to "merge", and provide a new name and description for the combined concept.
        - If you are unsure, respond with action set to "distinct", and leave the new_name and new_description fields empty.
        - Always fill out the reasoning field to explain your decision.

        In some cases, the new concept needs to be re-labeled given the existing concept to fit better in the knowledge graph.
        In other cases, the new concept is distinct and should be added as a new entity, possibly with a new, more descriptive name.
        """

        logging.info(f"Conflict resolution prompt: {prompt}")

        cr_result = self.openai_client.conflict_resolution(prompt)
        logging.info(f"Conflict resolution result: {cr_result}")
        if cr_result and cr_result.action == "same":
            logger.info(f"Entity '{concept_a}' and '{concept_b}' are the same, making sure new references old")
            new_entity_name = concept_a
            # Update all relationships with the new entity name
            for relationship in knowledge_graph_data.relationships:
                if relationship.source_entity_name == concept_b:
                    relationship.source_entity_name = new_entity_name
                if relationship.target_entity_name == concept_b:
                    relationship.target_entity_name = new_entity_name
            new_entity.name = new_entity_name  # Update the entity name
        elif cr_result and cr_result.action == "merge":
            logger.info(f"Entity '{concept_a}' and '{concept_b}' are being merged into the same entity '{cr_result.new_name}'")
            new_entity_name = cr_result.new_name or entity_a.name
            new_entity_description = cr_result.new_description or entity_a.description
            self.entity_service.update_entity(entity_a.name, new_entity_name, new_entity_description)
            # Update all relationships with the new entity name
            for relationship in knowledge_graph_data.relationships:
                if relationship.source_entity_name == concept_b:
                    relationship.source_entity_name = new_entity_name
                if relationship.target_entity_name == concept_b:
                    relationship.target_entity_name = new_entity_name

            new_entity.name = new_entity_name
        elif cr_result and cr_result.action == "distinct":
            # Keep the existing entity as is and add the new entity
            if cr_result.new_name and len(cr_result.new_name) > 3:
                new_entity_name = cr_result.new_name
                new_entity_description = cr_result.new_description or entity_b.description
                self.entity_service.update_entity(entity_b.name, new_entity_name, new_entity_description)
                for relationship in knowledge_graph_data.relationships:
                    if relationship.source_entity_name == concept_b:
                        relationship.source_entity_name = new_entity_name
                    if relationship.target_entity_name == concept_b:
                        relationship.target_entity_name = new_entity_name
                new_entity.name = new_entity_name
            pass

        return knowledge_graph_data

    def merge_knowledge_graph(self, new_knowledge_graph_data: KnowledgeGraph) -> Optional[KnowledgeGraph]:

        for entity in new_knowledge_graph_data.entities:
            logger.info(f"Processing entity: {entity.name}")

            similar_entities_by_name = self.entity_service.find_similar_entities_by_name(entity.name)
            similar_entities_by_description = self.entity_service.find_similar_entities_by_description(entity.name, entity.description)
            similar_entities = similar_entities_by_name + similar_entities_by_description if similar_entities_by_name and similar_entities_by_description else similar_entities_by_name or similar_entities_by_description
            # Sort similar entities by similarity score

            if similar_entities:
                similar_entities.sort(key=lambda x: x[2], reverse=True)

                most_similar_entity = similar_entities[0]
                similar_entity_name = most_similar_entity[0]
                similarity_score = most_similar_entity[2]

                logger.info(f"Most similar entity: {similar_entity_name}, Similarity Score: {similarity_score}")

                if similarity_score >= 0.975 and entity.name != similar_entity_name:
                    logger.info(f"Entity '{entity.name}' is very similar to existing entity '{similar_entity_name}' with score {similarity_score}. Updating name.")
                    # Update all relationships with the new entity name
                    for relationship in new_knowledge_graph_data.relationships:
                        if relationship.source_entity_name == entity.name:
                            relationship.source_entity_name = similar_entity_name
                        if relationship.target_entity_name == entity.name:
                            relationship.target_entity_name = similar_entity_name
                    entity.name = similar_entity_name  # Update the entity name
                elif similarity_score >= 0.85:
                    logger.info(f"Entity '{entity.name}' has a similar entity '{similar_entity_name}' with a low similarity score of {similarity_score}.")
                    # TODO: Conflict resolution goes here!
                    existing_entity = self.entity_service.get_entity_by_name(similar_entity_name)
                    new_knowledge_graph_data = self.resolve_entity_insertion_conflict(new_knowledge_graph_data, existing_entity, entity)
                else:
                    logger.info(f"Entity '{entity.name}' has a similar entity '{similar_entity_name}' with a low similarity score of {similarity_score}.")

            node_id = self.entity_service.create_entity_node(entity)
            if node_id:
                entity.id = node_id
                logger.info(f"Entity '{entity.name}', Neo4j ID: {node_id}")
                self.entity_service.embed_entity(entity.name, entity.description) # Embed entity after node creation
            else:
                logger.warning(f"Failed to create Neo4j node for entity '{entity.name}'. Skipping relationships for this entity.")

        # Process relationships using the ID mapping
        for relationship in new_knowledge_graph_data.relationships:
            logger.info(
                f"Mapping relationship: Source {relationship.source_entity_name}, Target {relationship.target_entity_name}"
            )
            self.entity_service.create_relationship(relationship) # Still using neo4j_client directly for relationships
        return new_knowledge_graph_data

    def run_kg_generation_iterations(self, initial_prompt: str, max_iterations: int):
        """Runs the knowledge graph generation process for a specified number of iterations."""
        knowledge_graph_data: Optional[KnowledgeGraph] = None

        prompt = initial_prompt
        previous_node_name = None
        for i in range(max_iterations):
            logger.info(f"Starting iteration {i + 1}/{max_iterations}")

            ls_paths = self.entity_service.find_longest_shortest_paths()
            print(f"Longest Shortest paths: {ls_paths}")
            # Pick a random path from the longest shortest paths
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

            new_knowledge_graph_data = self.generate_knowledge_graph_data(reasoning_trace)

            if new_knowledge_graph_data and new_knowledge_graph_data.entities:
                logger.info(f"Found {len(new_knowledge_graph_data.entities)} new entities.")

                knowledge_graph_data = self.merge_knowledge_graph(new_knowledge_graph_data)

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

    def xrun_kg_generation_iterations(self, initial_prompt: str, max_iterations: int):
        """Runs the knowledge graph generation process for a specified number of iterations."""
        knowledge_graph_data: Optional[KnowledgeGraph] = None

        prompt = initial_prompt
        previous_node_name = None
        for i in range(max_iterations):
            logger.info(f"Starting iteration {i + 1}/{max_iterations}")

            ls_paths = self.entity_service.find_longest_shortest_paths()
            print(f"Longest Shortest paths: {ls_paths}")
            # Pick a random path from the longest shortest paths
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

            existing_entity_names = self.entity_service.get_entity_names()
            existing_entity_names_str = ", ".join(existing_entity_names)

            new_knowledge_graph_data = self.generate_knowledge_graph_data(reasoning_trace, existing_entity_names_str)

            if new_knowledge_graph_data and new_knowledge_graph_data.entities:
                logger.info(f"Found {len(new_knowledge_graph_data.entities)} new entities.")

                for entity in new_knowledge_graph_data.entities:
                    logger.info(f"Processing entity: {entity.name}")

                    # Check for similar entities and potentially update the entity name
                    same_concept_entity = None
                    for existing_entity_name in existing_entity_names:
                        same_concept = self.entity_service.is_same_concept(entity.name, existing_entity_name)
                        if same_concept:
                            # TODO: There are cases where the descriptions are completely different,
                            # but the names are very similar. Need to handle this somehow..
                            # Match on the name for now
                            same_concept_entity = existing_entity_name
                            break

                    if same_concept_entity:
                        logger.info(f"Entity '{entity.name}' is similar to existing entity '{same_concept_entity}' Updating name.")
                        entity.name = same_concept_entity  # Update the entity name

                    node_id = self.entity_service.create_entity_node(entity)
                    if node_id:
                        entity.id = node_id
                        logger.info(f"Entity '{entity.name}', Neo4j ID: {node_id}")
                        self.entity_service.embed_entity(entity.name, entity.description) # Embed entity after node creation
                    else:
                        logger.warning(f"Failed to create Neo4j node for entity '{entity.name}'. Skipping relationships for this entity.")

                # Process relationships using the ID mapping
                for relationship in new_knowledge_graph_data.relationships:
                    logger.info(
                        f"Mapping relationship: Source {relationship.source_entity_name}, Target {relationship.target_entity_name}"
                    )
                    self.entity_service.create_relationship(relationship) # Still using neo4j_client directly for relationships

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
