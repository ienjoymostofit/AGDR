from neo4j import GraphDatabase

# Connect to Neo4j
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'testtest'))

# Query nodes and relationships
with driver.session() as session:
    # Get all nodes
    print("Nodes:")
    result = session.run('MATCH (n) RETURN n.name, n.description, labels(n)')
    for record in result:
        name = record['n.name']
        description = record['n.description']
        labels = record['labels(n)']
        print(f"  - {name} ({', '.join(labels)}): {description}")
    
    # Get all relationships
    print("\nRelationships:")
    result = session.run('MATCH (a)-[r]->(b) RETURN a.name, type(r), b.name, properties(r)')
    for record in result:
        source = record['a.name']
        rel_type = record['type(r)']
        target = record['b.name']
        props = record['properties(r)']
        props_str = ", ".join([f"{k}: {v}" for k, v in props.items()]) if props else ""
        print(f"  - {source} --[{rel_type}]--> {target} {{{props_str}}}")

# Close the driver
driver.close()