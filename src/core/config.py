from typing import Annotated, Tuple
import logging

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

class ModelConfig(BaseModel):
    """Configuration for a specific language model."""

    model_name: Annotated[str, Field(description="The name of the language model to use.")]
    api_key: Annotated[str, Field(description="The API key for accessing the language model.")]
    base_url: Annotated[str, Field(description="The base URL for the language model API.")]

class Settings(BaseSettings):
    """Settings for the knowledge graph generation application."""

    reasoning_model_config: Annotated[ModelConfig, Field(description="Configuration for the reasoning model.")]
    entity_extraction_model_config: Annotated[ModelConfig, Field(description="Configuration for the entity extraction model.")]
    embedding_model_config: Annotated[ModelConfig, Field(description="Configuration for the embedding model.")]
    neo4j_uri: Annotated[str, Field(description="The URI for the Neo4j database.")]
    neo4j_user: Annotated[str, Field(description="The username for the Neo4j database.")]
    neo4j_password: Annotated[str, Field(description="The password for the Neo4j database.")]
    think_tags: Annotated[Tuple[str, str], Field(description="The tags used to delineate reasoning content.")]
    log_level: Annotated[str, Field(default="INFO", description="The logging level for the application.")]

    # Flattened PgVectorConfig fields
    pgvector_dbname: Annotated[str, Field(env="PGVECTOR_DBNAME", description="The database name for PgVector.")]
    pgvector_user: Annotated[str, Field(env="PGVECTOR_USER", description="The username for PgVector.")]
    pgvector_password: Annotated[str, Field(env="PGVECTOR_PASSWORD", description="The password for PgVector.")]
    pgvector_host: Annotated[str, Field(env="PGVECTOR_HOST", description="The host for PgVector.")]
    pgvector_port: Annotated[int, Field(default=5432, env="PGVECTOR_PORT", description="The port for PgVector.")]
    pgvector_table_name: Annotated[str, Field(default="entity_embeddings", env="PGVECTOR_TABLE_NAME", description="The table name for entity embeddings in PgVector.")]
    pgvector_vector_dimension: Annotated[int, Field(default=1536, env="PGVECTOR_VECTOR_DIMENSION", description="The vector dimension for embeddings in PgVector.")]

    @classmethod
    def configure_logging(cls, level: str = "INFO"):
        """Configures the logging for the application."""
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
