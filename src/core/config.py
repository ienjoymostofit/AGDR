import logging
from typing import Tuple

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ModelConfig(BaseModel):
    """Configuration for a specific language model."""

    model_name: str = Field(..., description="The name of the language model to use.")
    api_key: str = Field(..., description="The API key for accessing the language model.")
    base_url: str = Field(..., description="The base URL for the language model API.")


class Settings(BaseSettings):
    """Settings for the knowledge graph generation application."""

    reasoning_model_config: ModelConfig = Field(
        ..., validation_alias="REASONING_MODEL_CONFIG", description="Configuration for the reasoning model."
    )
    entity_extraction_model_config: ModelConfig = Field(
        ..., validation_alias="ENTITY_EXTRACTION_MODEL_CONFIG", description="Configuration for the entity extraction model."
    )
    embedding_model_config: ModelConfig = Field(
        ..., validation_alias="EMBEDDING_MODEL_CONFIG", description="Configuration for the embedding model."
    )
    neo4j_uri: str = Field(..., validation_alias="NEO4J_URI", description="The URI for the Neo4j database.")
    neo4j_user: str = Field(..., validation_alias="NEO4J_USER", description="The username for the Neo4j database.")
    neo4j_password: str = Field(..., validation_alias="NEO4J_PASSWORD", description="The password for the Neo4j database.")
    think_tags: Tuple[str, str] = Field(
        ..., validation_alias="THINK_TAGS", description="The tags used to delineate reasoning content."
    )

    log_level: str = Field("INFO", validation_alias="LOG_LEVEL", description="The logging level for the application.")

    @classmethod
    def configure_logging(cls, level: str = "INFO"):
        """Configures the logging for the application."""
        logging.basicConfig(
            level=level, format="%(asctime)s - %(levelname)s - %(module)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
