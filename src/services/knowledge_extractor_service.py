import logging
import os
import sys
from typing import Optional

from core.interfaces import KnowledgeExtractor, LLMClient
from core.models import KnowledgeGraph

logger = logging.getLogger(__name__)

class KnowledgeExtractorService(KnowledgeExtractor):
    """Service for extracting knowledge graphs from text."""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize the knowledge extractor service.
        
        Args:
            llm_client: The language model client used for knowledge extraction
        """
        self.llm_client = llm_client
    
    def extract_knowledge_graph(self, text: str) -> Optional[KnowledgeGraph]:
        """
        Extracts a knowledge graph from the provided text.
        
        Uses a prompt template to guide the LLM in extracting structured knowledge.
        """
        # Load the prompt template from file
        prompt_path = os.path.join(sys.path[0], "prompts/extract_entities_and_relationships.md")
        try:
            with open(prompt_path, "r") as f:
                prompt_template = f.read()
        except Exception as e:
            logger.error(f"Failed to load knowledge extraction prompt template: {e}")
            return None
        
        # Construct the full prompt with the input text
        prompt = f"{prompt_template}\n<content>\n{text}\n</content>\n"
        
        logger.info("Extracting knowledge graph from text")
        
        # Use the LLM to extract the knowledge graph
        knowledge_graph = self.llm_client.extract_knowledge_graph(prompt)
        
        if knowledge_graph:
            logger.info(f"Extracted knowledge graph with {len(knowledge_graph.entities)} entities and {len(knowledge_graph.relationships)} relationships")
        else:
            logger.warning("Failed to extract knowledge graph from text")
        
        return knowledge_graph