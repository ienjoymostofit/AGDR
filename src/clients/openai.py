import json
import logging
from typing import Optional, Tuple

import openai
from openai import OpenAI
from pydantic import ValidationError

from core.models import KnowledgeGraph
from core.config import ModelConfig

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Client for interacting with the OpenAI API."""

    def __init__(self, think_tags: Tuple[str, str], reasoning_model_config: ModelConfig, entity_extraction_model_config: ModelConfig, ):
        """Initializes the OpenAIClient with API key and other configurations."""
        self.think_tags = think_tags
        self.reasoning_model_config = reasoning_model_config
        self.entity_extraction_model_config = entity_extraction_model_config
        self.reasoning_client = OpenAI(api_key=self.reasoning_model_config.api_key, base_url=self.reasoning_model_config.base_url)
        self.ee_client = OpenAI(api_key=self.entity_extraction_model_config.api_key, base_url=self.entity_extraction_model_config.base_url)

    def generate_reasoning_trace(self, prompt: str) -> Optional[str]:
        """Generates a reasoning trace from the specified language model."""
        try:
            response = self.reasoning_client.chat.completions.create(
                model=self.reasoning_model_config.model_name,
                stream=True,
                stop=self.think_tags[1],
                messages=[
                    {"role": "system", "content": f"You MUST always output {self.think_tags[0]} content, never leave it empty!"},
                    {"role": "user", "content": prompt},
                ],
            )
            max_chunks = 2000
            nchunks = 0
            content = ""
            for chunk in response:
                text = chunk.choices[0].delta.content
                if text:
                    print(text, end="", flush=True)  # Stream output to stdout
                    content += text
                # Sometimes deepthinker repeats it's start tag token..
                if content.endswith(self.think_tags[1]) or content.endswith(self.think_tags[0]):
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

    def generate_structured_data(self, prompt: str) -> Optional[KnowledgeGraph]:
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

    def generate_prompt(self, knowledge_graph_data: KnowledgeGraph, original_prompt: str) -> Optional[str]:
        """Generates a new prompt for reasoning based on the current knowledge graph."""
        prompt_text = f"""{json.dumps(knowledge_graph_data.to_dict(), indent=2)}\nFrom the knowledge graph above, generate a new natural language prompt for an LLM, with the intent to extend the knowledge with at least one new concept.

        The original query from the user was: "{original_prompt}"

        Formulate the new prompt as an open-ended question that addresses a totally new aspect of the existing concepts and relationships in the graph.

        Respond exclusively with the prompt.
        """
        logger.info(f"Generating new prompt with model: {self.entity_extraction_model_config.model_name}, Base URL: {self.entity_extraction_model_config.base_url}")
        try:
            response = self.ee_client.chat.completions.create(
                model=self.entity_extraction_model_config.model_name,
                stream=False,  # No need to stream this prompt generation
                messages=[{"role": "user", "content": prompt_text}],
            )
            if response.choices[0] and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
            else:
                logger.warning(
                    f"No content received from OpenAI for prompt generation. Model: {self.entity_extraction_model_config.model_name}, Base URL: {self.entity_extraction_model_config.base_url}"
                )
                return None
        except openai.APIError as e:
            logger.error(
                f"OpenAI API error during prompt generation: {e} - Model: {self.entity_extraction_model_config.model_name}, Base URL: {self.entity_extraction_model_config.base_url}"
            )
            return None
        except Exception as e:
            logger.exception(
                f"Unexpected error during prompt generation: {e} - Model: {self.entity_extraction_model_config.model_name}, Base URL: {self.entity_extraction_model_config.base_url}"
            )
            return None
