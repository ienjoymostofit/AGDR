import json
import logging
from typing import Optional, Tuple, Any

import openai
from openai import OpenAI
from pydantic import ValidationError

from core.models import ConflictResolutionResult, KnowledgeGraph
from core.config import ModelConfig
from core.interfaces import LLMClient

logger = logging.getLogger(__name__)

class OpenAIClient(LLMClient):
    """Client for interacting with the OpenAI API that implements the LLMClient interface."""

    def __init__(self, think_tags: Tuple[str, str], reasoning_model_config: ModelConfig, entity_extraction_model_config: ModelConfig, conflict_resolution_model_config: ModelConfig):
        """Initializes the OpenAIClient with API key and other configurations."""
        self.think_tags = think_tags
        self.reasoning_model_config = reasoning_model_config
        self.entity_extraction_model_config = entity_extraction_model_config
        self.conflict_resolution_model_config = conflict_resolution_model_config
        self.reasoning_client = OpenAI(api_key=self.reasoning_model_config.api_key, base_url=self.reasoning_model_config.base_url)
        self.ee_client = OpenAI(api_key=self.entity_extraction_model_config.api_key, base_url=self.entity_extraction_model_config.base_url)
        self.cr_client = OpenAI(api_key=self.conflict_resolution_model_config.api_key, base_url=self.conflict_resolution_model_config.base_url)

    def conflict_resolution(self, prompt: str) -> Optional[ConflictResolutionResult]:
        try:
            response = self.cr_client.chat.completions.create(
                model=self.conflict_resolution_model_config.model_name,
                stream=False,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            logger.info(f"Received content from OpenAI for conflict resolution: {content}")
            if not content:
                logger.warning(
                    f"No content received from OpenAI for conflict resolution. Model: {self.conflict_resolution_model_config.model_name}, Base URL: {self.conflict_resolution_model_config.base_url}"
                )
                return None

            try:
                structured_data = json.loads(content)
                return ConflictResolutionResult(**structured_data)  # Pydantic validation here
            except json.JSONDecodeError as e:
                logger.error(
                    f"JSONDecodeError: {e} - Content received: {content} - Model: {self.conflict_resolution_model_config.model_name}, Base URL: {self.conflict_resolution_model_config.base_url}"
                )
                return None
            except ValidationError as e:
                logger.error(
                    f"Pydantic ValidationError: {e} - Content received: {content} - Model: {self.conflict_resolution_model_config.model_name}, Base URL: {self.conflict_resolution_model_config.base_url}"
                )
                return None

        except openai.APIError as e:
            logger.error(
                f"OpenAI API error during conflict resolution: {e} - Model: {self.conflict_resolution_model_config.model_name}, Base URL: {self.conflict_resolution_model_config.base_url}"
            )
            return None

        return None

    def generate_reasoning_trace(self, prompt: str) -> Optional[str]:
        """Generates a reasoning trace from the specified language model."""
        try:
            if self.reasoning_model_config.prefix_message:
                messages = [json.loads(self.reasoning_model_config.prefix_message)]
            else:
                messages = []
            messages.extend([
                {"role": "system", "content": f"You MUST always output {self.think_tags[0]} content, never leave it empty!"},
                {"role": "user", "content": prompt}
            ])
            response = self.reasoning_client.chat.completions.create(
                model=self.reasoning_model_config.model_name,
                stream=True,
                stop=self.think_tags[1],
                messages=messages,
            )
            max_chunks = 4000  # Limit the number of chunks to prevent infinite loops
            nchunks = 0
            content = ""
            for chunk in response:
                text = chunk.choices[0].delta.content
                if text:
                    print(text, end="", flush=True)  # Stream output to stdout
                    content += text
                # Sometimes deepthinker repeats it's start tag token..
                if content.endswith(self.think_tags[1]) or (len(content) > len(self.think_tags[0])*2 and content.endswith(self.think_tags[0])):
                    print("\nEarly stopping reasoning trace..")
                    break
                nchunks += 1
                if nchunks >= max_chunks:
                    logger.warning(f"Max chunks reached for reasoning trace generation. Stopping early.")
                    break
            return content.strip()
        except openai.APIError as e:
            logger.error(
                f"OpenAI API error during reasoning trace generation: {e} - Model: {self.reasoning_model_config.model_name}, Base URL: {self.reasoning_model_config.base_url}"
            )
            return None
        except Exception as e:
            logger.exception(
                f"Unexpected error during reasoning trace generation: {e} - Model: {self.reasoning_model_config.model_name}, Base URL: {self.reasoning_model_config.base_url}"
            )
            return None

    def extract_knowledge_graph(self, prompt: str) -> Optional[KnowledgeGraph]:
        """Generates structured knowledge graph data."""
        try:
            response = self.ee_client.chat.completions.create(
                model=self.entity_extraction_model_config.model_name,
                stream=True,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )

            content = ""
            for chunk in response:
                text = chunk.choices[0].delta.content
                if text:
                    print(text, end="", flush=True)  # Stream output to stdout
                    content += text

            if not content:
                logger.warning(
                    f"No content received from OpenAI for structured data generation. Model: {self.entity_extraction_model_config.model_name}, Base URL: {self.entity_extraction_model_config.base_url}"
                )
                return None

            try:
                structured_data = json.loads(content)
                return KnowledgeGraph(**structured_data)  # Pydantic validation here
            except json.JSONDecodeError as e:
                logger.error(
                    f"JSONDecodeError: {e} - Content received: {content} - Model: {self.entity_extraction_model_config.model_name}, Base URL: {self.entity_extraction_model_config.base_url}"
                )
                return None
            except ValidationError as e:
                logger.error(
                    f"Pydantic ValidationError: {e} - Content received: {content} - Model: {self.entity_extraction_model_config.model_name}, Base URL: {self.entity_extraction_model_config.base_url}"
                )
                return None

        except openai.APIError as e:
            logger.error(
                f"OpenAI API error during structured data generation: {e} - Model: {self.entity_extraction_model_config.model_name}, Base URL: {self.entity_extraction_model_config.base_url}"
            )
            return None
        except Exception as e:
            logger.exception(
                f"Unexpected error during structured data generation: {e} - Model: {self.entity_extraction_model_config.model_name}, Base URL: {self.entity_extraction_model_config.base_url}"
            )
            return None
