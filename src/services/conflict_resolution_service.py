import logging
import json
from typing import Optional, Dict, Any

from core.interfaces import ConflictResolver, LLMClient
from core.models import Entity, ConflictResolutionResult
from services.entity_service import EntityService

logger = logging.getLogger(__name__)

class ConflictResolutionService(ConflictResolver):
    """Service for resolving conflicts between entities."""

    def __init__(self, llm_client: LLMClient, entity_service: EntityService):
        """
        Initialize the conflict resolution service.

        Args:
            llm_client: The language model client used for resolving conflicts
            entity_service: The entity service for accessing entity information
        """
        self.llm_client = llm_client
        self.entity_service = entity_service

    def resolve_entity_conflict(self, existing_entity: Entity, new_entity: Entity,
                               context: Optional[Dict[str, Any]] = None) -> ConflictResolutionResult:
        """
        Resolves a conflict between an existing entity and a new entity.

        Uses an LLM to determine if the entities are the same, should be merged, or kept distinct.
        """
        concept_a = existing_entity.name
        concept_b = new_entity.name

        # Get subgraph information to provide context for the conflict resolution
        concept_a_subgraph = self.entity_service.get_entity_subgraph(concept_a, 1)
        concept_b_subgraph = self.entity_service.get_entity_subgraph(concept_b, 1)

        if concept_a_subgraph.entities:
            concept_a_subgraph_prompt = f"**Subgraph:**\n ```json\n {json.dumps(concept_a_subgraph.to_dict(), indent=2)}\n```"
        else:
            concept_a_subgraph_prompt = ""

        if concept_b_subgraph.entities:
            concept_b_subgraph_prompt = f"**Subgraph:**\n ```json\n {json.dumps(concept_b_subgraph.to_dict(), indent=2)}\n```"
        else:
            concept_b_subgraph_prompt = ""

        # Construct the prompt for the conflict resolution
        prompt = f"""
        You are building a knowledge graph, and you have encountered a potential conflict between two concepts when adding a newly discovered entity.

        When building a knowledge graph, it is essential to ensure that the concepts are distinct and do not overlap.

        Given the two concepts below, your task is to determine if they are the same, or different concepts.

        ## Concept A (Existing):
        **Name:** {concept_a}
        **Description:** {existing_entity.description}
        {concept_a_subgraph_prompt}

        ## Concept B (New):
        **Name:** {concept_b}
        **Description:** {new_entity.description}
        {concept_b_subgraph_prompt}

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

        logger.info(f"Generating conflict resolution for entities: {concept_a} and {concept_b}")

        # Get the conflict resolution result from the LLM
        cr_result = self.llm_client.conflict_resolution(prompt)
        if not cr_result:
            # Default to distinct if we couldn't get a resolution
            logger.warning(f"Failed to get conflict resolution result for {concept_a} and {concept_b}. Defaulting to distinct.")
            cr_result = ConflictResolutionResult(
                reasoning="Failed to get a resolution from the LLM, defaulting to distinct.",
                action="distinct",
                new_name=None,
                new_description=None
            )

        logger.info(f"Conflict resolution result: Action={cr_result.action}, New name={cr_result.new_name}")
        return cr_result
