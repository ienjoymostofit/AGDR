from pydantic_settings import BaseSettings
from pydantic import Field, BaseModel
from typing import Tuple

class ModelConfig(BaseModel):
    """Configuration for a specific OpenAI model."""
    model_name: str
    api_key: str
    base_url: str # Base URL is now required here

class Settings(BaseSettings):
    """Settings for the knowledge graph generation application."""
    reasoning_model_config: ModelConfig = Field(..., validation_alias="REASONING_MODEL_CONFIG")
    entity_extraction_model_config: ModelConfig = Field(..., validation_alias="ENTITY_EXTRACTION_MODEL_CONFIG")
    embedding_model_config: ModelConfig = Field(..., validation_alias="EMBEDDING_MODEL_CONFIG")
    neo4j_uri: str = Field(..., validation_alias="NEO4J_URI")
    neo4j_user: str = Field(..., validation_alias="NEO4J_USER")
    neo4j_password: str = Field(..., validation_alias="NEO4J_PASSWORD")
    think_tags: Tuple[str, str] = Field(..., validation_alias="THINK_TAGS")
