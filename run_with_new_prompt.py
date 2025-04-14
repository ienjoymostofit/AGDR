import os
import sys

# Add src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
from core.config import Settings
from core.factory import ServiceFactory

# Load environment variables
load_dotenv()

def main():
    # Initialize settings and factory
    settings = Settings()
    factory = ServiceFactory(settings)
    
    # Clear the Neo4j database
    graph_db = factory.get_graph_database()
    try:
        with graph_db._driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n").consume()
        print("Cleared Neo4j database.")
    except Exception as e:
        print(f"Error clearing Neo4j database: {e}")
    
    # Get the knowledge graph generator
    kg_generator = factory.get_knowledge_graph_generator()
    
    # New prompt about Greek philosophers
    prompt = "Tell me about the ancient Greek philosophers and their contributions to science and philosophy."
    
    # Generate knowledge graph
    print(f"Generating knowledge graph for prompt: '{prompt}'")
    kg_generator.run_kg_generation_iterations(prompt, max_iterations=3)
    
    print("Knowledge graph generation completed.")
    print("You can view the graph at: https://work-1-zwzrujpnbtpftrfq.prod-runtime.all-hands.dev/")

if __name__ == "__main__":
    main()