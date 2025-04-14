import logging
from typing import Dict, Any

from core.config import Settings, ModelConfig
from core.interfaces import GraphDatabase, VectorDatabase, LLMClient, EmbeddingProvider
from clients.neo4j import Neo4jClient
from clients.pgvector import PgVectorClient
from clients.openai import OpenAIClient
from clients.mock_openai import MockOpenAIClient
from services.embedder import Embedder
from services.mock_embedder import MockEmbedder
from services.embed_service import EmbedService
from services.entity_service import EntityService
from services.knowledge_graph_generator import KnowledgeGraphGenerator
from services.reasoning_service import LLMReasoningService
from services.knowledge_extractor_service import KnowledgeExtractorService
from services.conflict_resolution_service import ConflictResolutionService
from services.graph_population_service import GraphPopulationService

logger = logging.getLogger(__name__)

class ServiceFactory:
    """Factory class for creating and managing service instances."""
    
    def __init__(self, settings: Settings):
        """Initializes the ServiceFactory with application settings."""
        self.settings = settings
        self._instances: Dict[str, Any] = {}
        
    def get_graph_database(self) -> GraphDatabase:
        """Returns a GraphDatabase implementation."""
        if "graph_db" not in self._instances:
            self._instances["graph_db"] = Neo4jClient(
                self.settings.neo4j_uri,
                self.settings.neo4j_user,
                self.settings.neo4j_password
            )
        return self._instances["graph_db"]
    
    def get_vector_database(self) -> VectorDatabase:
        """Returns a VectorDatabase implementation."""
        if "vector_db" not in self._instances:
            self._instances["vector_db"] = PgVectorClient(
                dbname=self.settings.pgvector_dbname,
                user=self.settings.pgvector_user,
                password=self.settings.pgvector_password,
                host=self.settings.pgvector_host,
                port=self.settings.pgvector_port,
                table_name=self.settings.pgvector_table_name,
                vector_dimension=self.settings.pgvector_vector_dimension,
            )
        return self._instances["vector_db"]
    
    def get_llm_client(self) -> LLMClient:
        """Returns a LLMClient implementation."""
        if "llm_client" not in self._instances:
            # Use MockOpenAIClient for testing
            self._instances["llm_client"] = MockOpenAIClient(
                self.settings.think_tags,
                self.settings.reasoning_model_config,
                self.settings.entity_extraction_model_config,
                self.settings.conflict_resolution_model_config
            )
            # Uncomment the following to use the real OpenAI client
            # self._instances["llm_client"] = OpenAIClient(
            #     self.settings.think_tags,
            #     self.settings.reasoning_model_config,
            #     self.settings.entity_extraction_model_config,
            #     self.settings.conflict_resolution_model_config
            # )
        return self._instances["llm_client"]
    
    def get_embedding_provider(self) -> EmbeddingProvider:
        """Returns an EmbeddingProvider implementation."""
        if "embedding_provider" not in self._instances:
            # Use MockEmbedder for testing
            self._instances["embedding_provider"] = MockEmbedder(self.settings.embedding_model_config)
            # Uncomment the following to use the real Embedder
            # self._instances["embedding_provider"] = Embedder(self.settings.embedding_model_config)
        return self._instances["embedding_provider"]
    
    def get_reasoning_service(self) -> LLMReasoningService:
        """Returns a ReasoningService implementation."""
        if "reasoning_service" not in self._instances:
            llm_client = self.get_llm_client()
            self._instances["reasoning_service"] = LLMReasoningService(llm_client)
        return self._instances["reasoning_service"]
    
    def get_knowledge_extractor(self) -> KnowledgeExtractorService:
        """Returns a KnowledgeExtractor implementation."""
        if "knowledge_extractor" not in self._instances:
            llm_client = self.get_llm_client()
            self._instances["knowledge_extractor"] = KnowledgeExtractorService(llm_client)
        return self._instances["knowledge_extractor"]
    
    def get_conflict_resolver(self) -> ConflictResolutionService:
        """Returns a ConflictResolver implementation."""
        if "conflict_resolver" not in self._instances:
            llm_client = self.get_llm_client()
            entity_service = self.get_entity_service()
            self._instances["conflict_resolver"] = ConflictResolutionService(llm_client, entity_service)
        return self._instances["conflict_resolver"]
    
    def get_graph_populator(self) -> GraphPopulationService:
        """Returns a GraphPopulator implementation."""
        if "graph_populator" not in self._instances:
            graph_db = self.get_graph_database()
            embed_service = self.get_embed_service()
            conflict_resolver = self.get_conflict_resolver()
            self._instances["graph_populator"] = GraphPopulationService(graph_db, embed_service, conflict_resolver)
        return self._instances["graph_populator"]
    
    def get_embed_service(self) -> EmbedService:
        """Returns an EmbedService instance."""
        if "embed_service" not in self._instances:
            vector_db = self.get_vector_database()
            embedding_provider = self.get_embedding_provider()
            self._instances["embed_service"] = EmbedService(vector_db, embedding_provider)
        return self._instances["embed_service"]
    
    def get_entity_service(self) -> EntityService:
        """Returns an EntityService instance."""
        if "entity_service" not in self._instances:
            embed_service = self.get_embed_service()
            graph_db = self.get_graph_database()
            self._instances["entity_service"] = EntityService(embed_service, graph_db)
        return self._instances["entity_service"]
    
    def get_knowledge_graph_generator(self) -> KnowledgeGraphGenerator:
        """Returns a KnowledgeGraphGenerator instance."""
        if "kg_generator" not in self._instances:
            reasoning_service = self.get_reasoning_service()
            knowledge_extractor = self.get_knowledge_extractor()
            graph_populator = self.get_graph_populator()
            entity_service = self.get_entity_service()
            self._instances["kg_generator"] = KnowledgeGraphGenerator(
                reasoning_service,
                knowledge_extractor, 
                graph_populator,
                entity_service
            )
        return self._instances["kg_generator"]
    
    def close_all(self) -> None:
        """Closes all resources."""
        if "graph_db" in self._instances:
            self._instances["graph_db"].close()
        if "vector_db" in self._instances and hasattr(self._instances["vector_db"], "close"):
            self._instances["vector_db"].close()
        self._instances = {}
        logger.info("All service resources closed.")