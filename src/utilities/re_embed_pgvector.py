import logging
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from core.config import Settings
from clients.pgvector import PgVectorClient
from services.embedder import Embedder
from services.embed_service import EmbedService

def main():
    """
    Main entry point
    """
    load_dotenv()

    # Instantiate settings once
    SETTINGS = Settings()
    SETTINGS.configure_logging(SETTINGS.log_level)

    logger = logging.getLogger(__name__)
    pgvector_client = PgVectorClient(
        dbname=SETTINGS.pgvector_dbname,
        user=SETTINGS.pgvector_user,
        password=SETTINGS.pgvector_password,
        host=SETTINGS.pgvector_host,
        port=SETTINGS.pgvector_port,
        table_name=SETTINGS.pgvector_table_name,
        vector_dimension=SETTINGS.pgvector_vector_dimension,
    )
    embedder = Embedder(SETTINGS.embedding_model_config)
    pgvector_service = EmbedService(pgvector_client, embedder)

    batch_size = 100
    last_id = 0
    while True:
        entities = pgvector_client.get_entities_from_last_id(last_id, batch_size)
        if not entities:
            break
        for entity in entities:
            pgvector_service.embed_entity(entity.name, entity.description)
            last_id = entity.id


if __name__ == "__main__":
    main()
