import logging
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from core.config import Settings
from core.factory import ServiceFactory

def main():
    """
    Main entry point
    """
    load_dotenv()

    # Instantiate settings once
    SETTINGS = Settings()
    SETTINGS.configure_logging(SETTINGS.log_level)

    logger = logging.getLogger(__name__)
    # Initialize service factory
    service_factory = ServiceFactory(SETTINGS)
    
    # Get the embed service through the factory
    embed_service = service_factory.get_embed_service()
    # Get the vector database for accessing entities
    vector_db = service_factory.get_vector_database()

    try:
        batch_size = 100
        last_id = 0
        while True:
            entities = vector_db.get_entities_from_last_id(last_id, batch_size)
            if not entities:
                break
            for entity in entities:
                embed_service.embed_entity(entity.name, entity.description)
                last_id = entity.id
    finally:
        # Clean up all resources
        service_factory.close_all()


if __name__ == "__main__":
    main()
