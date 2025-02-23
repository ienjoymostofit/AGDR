import sys
import logging
from dotenv import load_dotenv
from kg_gen import KnowledgeGraphGenerator
from neo4j_client import Neo4jClient
from openai_client import OpenAIClient
from settings import Settings

load_dotenv()

settings = Settings()  # type: ignore [call-arg]

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(module)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Main Execution ---
if __name__ == "__main__":
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

    openai_client = OpenAIClient(settings.think_tags)
    neo4j_client = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    kg_generator = KnowledgeGraphGenerator(openai_client, neo4j_client, settings)

    try:
        kg_generator.run_kg_generation_iterations(initial_prompt, max_iterations)
    except Exception as e:
        logger.exception("Unhandled exception during knowledge graph generation process.")
        print(f"An unexpected error occurred: {e}")
        sys.exit(2)
    finally:
        neo4j_client.close()
        logger.info("Application finished.")
