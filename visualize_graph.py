import networkx as nx
import matplotlib.pyplot as plt
from neo4j import GraphDatabase
import os

# Connect to Neo4j
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'testtest'))

# Create a directed graph
G = nx.DiGraph()

# Query nodes and relationships
with driver.session() as session:
    # Get all nodes
    result = session.run('MATCH (n) RETURN n')
    for record in result:
        node = record['n']
        G.add_node(node['name'], description=node['description'])
    
    # Get all relationships
    result = session.run('MATCH (a)-[r]->(b) RETURN a.name, type(r), b.name')
    for record in result:
        source = record['a.name']
        target = record['b.name']
        rel_type = record['type(r)']
        G.add_edge(source, target, type=rel_type)

# Close the driver
driver.close()

# Create the visualization
plt.figure(figsize=(12, 8))
pos = nx.spring_layout(G, seed=42)  # positions for all nodes

# Draw nodes
nx.draw_networkx_nodes(G, pos, node_size=700, node_color='lightblue')

# Draw edges
nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.7, arrowsize=20)

# Draw node labels
nx.draw_networkx_labels(G, pos, font_size=10, font_family='sans-serif')

# Draw edge labels
edge_labels = {(u, v): d['type'] for u, v, d in G.edges(data=True)}
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)

# Save the figure
plt.axis('off')
plt.tight_layout()
plt.savefig('knowledge_graph.png', dpi=300, bbox_inches='tight')
print("Graph visualization saved as 'knowledge_graph.png'")