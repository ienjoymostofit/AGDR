import json
import logging
from typing import Optional, Tuple
import openai
from pydantic import ValidationError
from models import KnowledgeGraph
from settings import ModelConfig

# --- OpenAI Client ---
class OpenAIClient:
    """Class for interacting with the LLM, supporting multiple base URLs and API keys."""

    def __init__(self, think_tags=Tuple[str, str]):
        self.think_tags = think_tags
        self.logger = logging.getLogger(__name__)

    def generate_reasoning_trace(self, model_config: ModelConfig, prompt: str) -> Optional[str]:
        """Generates a reasoning trace from the specified language model, using provided config."""
        try:
            client = openai.OpenAI(api_key=model_config.api_key, base_url=model_config.base_url) # Instantiate client per call
            response = client.chat.completions.create(
                model=model_config.model_name, # Use model name from config
                stream=True,
                stop=self.think_tags[1],
                messages=[
                    {"role": "system", "content": f"You MUST always output {self.think_tags[0]} content, never leave it empty!"},
                    {"role": "user", "content": prompt},
                ],
            )
            content = ""
            for chunk in response:
                text = chunk.choices[0].delta.content
                if text:
                    print(text, end="", flush=True)  # Stream output to stdout
                    content += text
                if content.endswith(self.think_tags[1]):
                    print("\nEarly stopping reasoning trace..")
                    break
            return content.strip()
        except openai.APIError as e:
            logger.error(f"OpenAI API error during reasoning trace generation: {e} - Model: {model_config.model_name}, Base URL: {model_config.base_url}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error during reasoning trace generation: {e} - Model: {model_config.model_name}, Base URL: {model_config.base_url}")
            return None

    def generate_structured_data(self, model_config: ModelConfig, prompt: str) -> Optional[KnowledgeGraph]:
        """Generates structured knowledge graph data, using provided model config."""
        try:
            client = openai.OpenAI(api_key=model_config.api_key, base_url=model_config.base_url) # Instantiate client per call
            response = client.chat.completions.create(
                model=model_config.model_name, # Use model name from config
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
                logger.warning(f"No content received from OpenAI for structured data generation. Model: {model_config.model_name}, Base URL: {model_config.base_url}")
                return None

            try:
                structured_data = json.loads(content)
                return KnowledgeGraph(**structured_data)  # Pydantic validation here
            except json.JSONDecodeError as e:
                logger.error(f"JSONDecodeError: {e} - Content received: {content} - Model: {model_config.model_name}, Base URL: {model_config.base_url}")
                return None
            except ValidationError as e:
                logger.error(f"Pydantic ValidationError: {e} - Content received: {content} - Model: {model_config.model_name}, Base URL: {model_config.base_url}")
                return None

        except openai.APIError as e:
            logger.error(f"OpenAI API error during structured data generation: {e} - Model: {model_config.model_name}, Base URL: {model_config.base_url}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error during structured data generation: {e} - Model: {model_config.model_name}, Base URL: {model_config.base_url}")
            return None

    def generate_prompt(self, model_config: ModelConfig, knowledge_graph_data: KnowledgeGraph, original_prompt: str) -> Optional[str]:
        """Generates a new prompt for reasoning based on the current knowledge graph, using provided model config."""

        prompt_text = f"""{json.dumps(knowledge_graph_data.to_dict(), indent=2)}\nFrom the knowledge graph above, generate a new natural language prompt for an LLM, with the intent to extend the knowledge with at least one new concept.

        The original query from the user was: "{original_prompt}"

        Formulate the new prompt as an open-ended question that addresses a totally new aspect of the existing concepts and relationships in the graph.

        Respond exclusively with the prompt.
        """
        logger.info(f"Generating new prompt with model: {model_config.model_name}, Base URL: {model_config.base_url}")
        try:
            client = openai.OpenAI(api_key=model_config.api_key, base_url=model_config.base_url) # Instantiate client per call
            response = client.chat.completions.create(
                model=model_config.model_name, # Use model name from config
                stream=False, # No need to stream this prompt generation
                messages=[{"role": "user", "content": prompt_text}],
            )
            if response.choices[0] and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
            else:
                logger.warning(f"No content received from OpenAI for prompt generation. Model: {model_config.model_name}, Base URL: {model_config.base_url}")
                return None
        except openai.APIError as e:
            logger.error(f"OpenAI API error during prompt generation: {e} - Model: {model_config.model_name}, Base URL: {model_config.base_url}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error during prompt generation: {e} - Model: {model_config.model_name}, Base URL: {model_config.base_url}")
            return None
