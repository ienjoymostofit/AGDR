import sys
import logging
import os

from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

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

    if len(sys.argv) < 3:
        print("Usage: python knowledge_graph_generation.py <prompt> <iterations>")
        sys.exit(1)

    initial_prompt = sys.argv[1]
    try:
        max_iterations = int(sys.argv[2])
        if max_iterations <= 0:
            raise ValueError("Iterations must be a positive integer.")
    except ValueError:
        print("Error: Iterations must be a positive integer.")
        sys.exit(1)

    # Initialize service factory
    service_factory = ServiceFactory(SETTINGS)
    
    # Get the knowledge graph generator through the factory
    kg_generator = service_factory.get_knowledge_graph_generator()
    
    try:
        kg_generator.run_kg_generation_iterations(initial_prompt, max_iterations)
    except Exception as e:
        logger.exception("Unhandled exception during knowledge graph generation process.")
        print(f"An unexpected error occurred: {e}")
        sys.exit(2)
    finally:
        # Clean up all resources
        service_factory.close_all()
        logger.info("Application finished.")


if __name__ == "__main__":
    main()
