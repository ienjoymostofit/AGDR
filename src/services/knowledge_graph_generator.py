import logging
import random
from typing import Optional, List, Dict, Any

from core.interfaces import ReasoningService, KnowledgeExtractor, GraphPopulator
from services.entity_service import EntityService
from core.models import KnowledgeGraph

logger = logging.getLogger(__name__)

class KnowledgeGraphGenerator:
    """Orchestrates the knowledge graph generation process."""

    def __init__(
        self,
        reasoning_service: ReasoningService,
        knowledge_extractor: KnowledgeExtractor,
        graph_populator: GraphPopulator,
        entity_service: EntityService
    ):
        """
        Initialize the knowledge graph generator.

        Args:
            reasoning_service: Service for generating reasoning traces
            knowledge_extractor: Service for extracting knowledge graphs from text
            graph_populator: Service for populating the graph with entities and relationships
            entity_service: Service for entity-related operations
        """
        self.reasoning_service = reasoning_service
        self.knowledge_extractor = knowledge_extractor
        self.graph_populator = graph_populator
        self.entity_service = entity_service

    def run_kg_generation_iterations(self, initial_prompt: str, max_iterations: int) -> None:
        """
        Runs the knowledge graph generation process for a specified number of iterations.

        Args:
            initial_prompt: The initial prompt to start the generation process
            max_iterations: The maximum number of iterations to run
        """
        prompt = initial_prompt
        previous_node_name = None

        for i in range(max_iterations):
            logger.info(f"Starting iteration {i + 1}/{max_iterations}")

            # Find potential paths to explore
            longest_paths = self.entity_service.find_longest_shortest_paths()

            # Generate a new prompt based on the paths, if available
            if longest_paths and len(longest_paths) > 0:
                prompt = self._generate_next_prompt(longest_paths, previous_node_name)
                if prompt == previous_node_name:
                    # If we're exploring the same node, vary the prompt slightly
                    prompt = f"Expanding on the concept of {prompt}, what deeper insights and connections could we explore?"
                previous_node_name = prompt.split("(")[0].strip() if "(" in prompt else prompt
                logger.info(f"Generated prompt: {prompt}")
            else:
                # If no paths found, continue with the initial or current prompt
                logger.info(f"No paths found, using current prompt: {prompt}")

            # Generate reasoning trace
            reasoning_trace = self.reasoning_service.generate_reasoning_trace(prompt)
            if not reasoning_trace:
                logger.error("Failed to generate reasoning trace, stopping iterations.")
                break

            # Extract knowledge graph from reasoning trace
            knowledge_graph_data = self.knowledge_extractor.extract_knowledge_graph(reasoning_trace)

            if knowledge_graph_data and knowledge_graph_data.entities:
                logger.info(f"Extracted {len(knowledge_graph_data.entities)} entities and {len(knowledge_graph_data.relationships)} relationships")

                # Merge the new knowledge into the existing graph
                updated_kg = self.graph_populator.merge_knowledge_graph(knowledge_graph_data)

                # Log the results
                self._log_iteration_results(updated_kg)
            else:
                logger.info("No new entities extracted in this iteration.")

        logger.info("Knowledge graph generation process completed.")

    def _generate_next_prompt(self, paths: List[Dict[str, Any]], previous_node_name: Optional[str]) -> str:
        """
        Generates a prompt for the next iteration based on the available paths.

        Args:
            paths: List of paths in the graph
            previous_node_name: Name of the previously explored node

        Returns:
            A prompt for the next iteration
        """
        # Select a random path
        path = random.choice(paths)

        # Choose either the start or end node, avoiding the previously explored node
        start_node_name = path["endNodeName"]
        start_node_description = path["endNodeDescription"]

        if previous_node_name == start_node_name:
            start_node_name = path["startNodeName"]
            start_node_description = path["startNodeDescription"]

        # Create a prompt to explore this concept
        return f"Given the concept of '{start_node_name} ({start_node_description})', what related concepts and relationships can be explored to expand our knowledge graph?"

    def _log_iteration_results(self, knowledge_graph: KnowledgeGraph) -> None:
        """
        Logs the results of an iteration.

        Args:
            knowledge_graph: The knowledge graph data from the iteration
        """
        if knowledge_graph:
            logger.info("\n--- Entities added in this iteration ---")
            for entity in knowledge_graph.entities:
                logger.info(f"    - Name: {entity.name}")
                logger.info(f"      ID: {entity.id}")
                logger.info(f"      Categories: {entity.category}")

            logger.info("\n--- Relationships added in this iteration ---")
            for relationship in knowledge_graph.relationships:
                logger.info(f"    - Type: {relationship.relation_type}")
                logger.info(f"      Source: {relationship.source_entity_name}")
                logger.info(f"      Target: {relationship.target_entity_name}")
                logger.info(f"      Attributes: {relationship.attributes}")
