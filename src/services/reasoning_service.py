import logging
from typing import Optional

from core.interfaces import ReasoningService, LLMClient

logger = logging.getLogger(__name__)

class LLMReasoningService(ReasoningService):
    """Service for generating reasoning traces using a language model."""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize the reasoning service.
        
        Args:
            llm_client: The language model client used for generating reasoning
        """
        self.llm_client = llm_client
    
    def generate_reasoning_trace(self, prompt: str) -> Optional[str]:
        """
        Generates a reasoning trace from the given prompt using the LLM.
        """
        logger.info(f"Generating reasoning trace for prompt: {prompt[:100]}...")
        
        reasoning_trace = self.llm_client.generate_reasoning_trace(prompt)
        
        if reasoning_trace:
            logger.info(f"Generated reasoning trace of length: {len(reasoning_trace)}")
        else:
            logger.warning("Failed to generate reasoning trace")
            
        return reasoning_trace