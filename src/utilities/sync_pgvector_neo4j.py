import logging
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from core.config import Settings
from core.factory import ServiceFactory
from core.models import Entity

def main():
    """
    Main entry point for the data synchronization utility (Neo4j as source of truth).
    """
    load_dotenv()

    # Instantiate settings and configure logging
    settings = Settings()
    settings.configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)

    # Initialize service factory
    service_factory = ServiceFactory(settings)

    # Get the graph database and vector database
    graph_db = service_factory.get_graph_database()
    vector_db = service_factory.get_vector_database()
    embed_service = service_factory.get_embed_service()

    try:
        # 1. Query entity names and descriptions from Neo4j
        neo4j_entity_names = {}
        for entity_name in graph_db.query_node_names():
            entity = graph_db.get_node_by_name(entity_name)
            if entity:
                neo4j_entity_names[entity.name] = entity.description
            else:
                logger.warning(f"Could not retrieve description for entity {entity_name} from Neo4j.")

        logger.info(f"Found {len(neo4j_entity_names)} entities in Neo4j.")

        # 2. Query entity names from PgVector
        pgvector_entities = vector_db.get_entities_from_last_id(last_id=0, limit=100000) # Assuming a large limit
        if not pgvector_entities:
            logger.info("No entities found in PgVector.")
            pgvector_entity_names = set()
        else:
            pgvector_entity_names = {entity.name for entity in pgvector_entities}
        logger.info(f"Found {len(pgvector_entity_names)} entities in PgVector.")

        # 3. Identify entities that exist in Neo4j but not in PgVector
        missing_embeddings = set(neo4j_entity_names.keys()) - pgvector_entity_names
        logger.info(f"Found {len(missing_embeddings)} entities missing embeddings in PgVector.")

        # 4. Create missing embeddings in PgVector
        for entity_name, description in neo4j_entity_names.items():
            if entity_name in missing_embeddings:
                logger.info(f"Creating missing embedding in PgVector for entity: {entity_name}")
                try:
                    embed_service.embed_entity(entity_name, description)
                    logger.info(f"  Successfully created embedding for entity: {entity_name}")
                except Exception as e:
                    logger.error(f"  Error creating embedding for entity {entity_name}: {e}")

        # 5. Identify entities that exist in PgVector but not in Neo4j
        orphaned_embeddings = pgvector_entity_names - set(neo4j_entity_names.keys())
        logger.info(f"Found {len(orphaned_embeddings)} orphaned embeddings in PgVector.")

        # 6. Delete orphaned embeddings in PgVector
        for entity_name in orphaned_embeddings:
            logger.info(f"Deleting orphaned embedding in PgVector for entity: {entity_name}")
            try:
                embed_service.remove_entity(entity_name)
                logger.info(f"  Successfully deleted embedding for entity: {entity_name}")
            except Exception as e:
                logger.error(f"  Error deleting embedding for entity {entity_name}: {e}")

    finally:
        service_factory.close_all()
        logger.info("Data synchronization utility finished.")


if __name__ == "__main__":
    main()
