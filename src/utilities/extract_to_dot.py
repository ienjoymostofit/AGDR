# Export the full graph database as a dot file
import os
import sys
import re
from dotenv import load_dotenv

from core.config import Settings
from core.factory import ServiceFactory
from core.interfaces import GraphDatabase


class GraphExtractor:
    def __init__(self, graph_db: GraphDatabase):
        self.graph_db = graph_db

    def close(self):
        self.graph_db.close()

    def extract_graph(self):
        # For this utility, we need to adapt the raw query capability
        # This is a limitation of our interface for this specific use case
        # In a real-world application, we'd extend the GraphDatabase interface
        # to include this kind of raw query capability
        if hasattr(self.graph_db, '_driver'):
            with self.graph_db._driver.session() as session:
                result = session.run("""
                    MATCH (n)
                    OPTIONAL MATCH (n)-[r]->(m)
                    RETURN n.name AS name, n.description AS description, type(r) AS relationshipType, m.name AS connectedNodeName
                """)
                return list(result)
        else:
            raise NotImplementedError("The graph database implementation doesn't provide direct query access")

    def sanitize_identifier(self, name):
        # Remove special characters, replace spaces with underscores
        return re.sub(r'\W+', '_', name).strip('_')

    def to_dot(self, data):
        dot_str = "digraph G {\n"

        # Set graph attributes for compactness
        dot_str += '    rankdir=LR;\n'  # Set left-to-right orientation
        dot_str += '    size="8,5";\n'   # Define maximum size for the rendered graph
        dot_str += '    node [shape=box];\n'  # Use rectangular nodes for better visibility

        # Create a subgraph to group all nodes
        dot_str += '    subgraph cluster_main {\n'
        dot_str += '        label="Main Group";\n'  # Label for the subgraph

        node_mapping = {}

        for record in data:
            name = record["name"]
            description = record["description"]  # Keep description for tooltips
            connected_node = record["connectedNodeName"]
            relationship_type = record["relationshipType"]

            # Sanitize the name to create a safe identifier
            identifier = self.sanitize_identifier(name)
            node_mapping[name] = identifier

            # Add nodes with concise labels and tooltips for descriptions
            label = f"{name}"  # Only showing name in the label
            dot_str += f'        {identifier} [label="{label}", tooltip="{description}", style=filled, fillcolor=lightblue];\n'

        for record in data:
            name = record["name"]
            connected_node = record["connectedNodeName"]
            relationship_type = record["relationshipType"]

            if connected_node:
                # Get the identifiers for both nodes
                source_id = node_mapping[name]
                target_id = node_mapping[connected_node]

                # Add relationships using the node identifiers
                dot_str += f'        {source_id} -> {target_id} [label="{relationship_type}", penwidth=2];\n'  # Thicker edges for emphasis

        dot_str += '    }\n'  # End of subgraph
        dot_str += "}\n"
        return dot_str

    def save_to_file(self, dot_str, filename):
        with open(filename, 'w') as file:
            file.write(dot_str)


if __name__ == "__main__":
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

    load_dotenv()

    settings = Settings()
    # Initialize service factory
    service_factory = ServiceFactory(settings)
    
    # Get the graph database through the factory
    graph_db = service_factory.get_graph_database()
    
    extractor = GraphExtractor(graph_db)
    try:
        data = extractor.extract_graph()
        mermaid_output = extractor.to_dot(data)
        extractor.save_to_file(mermaid_output, "graph.dot")
    finally:
        service_factory.close_all()
