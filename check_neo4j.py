from neo4j import GraphDatabase

# Connect to Neo4j
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'testtest'))

# Query nodes
with driver.session() as session:
    print("Nodes:")
    result = session.run('MATCH (n) RETURN n')
    for record in result:
        print(record['n'])
    
    print("\nRelationship types:")
    result = session.run('MATCH ()-[r]->() RETURN DISTINCT type(r)')
    for record in result:
        print(record['type(r)'])
    
    print("\nRelationships:")
    result = session.run('MATCH (a)-[r]->(b) RETURN a.name, type(r), b.name')
    for record in result:
        print(f"{record['a.name']} --[{record['type(r)']}]--> {record['b.name']}")

# Close the driver
driver.close()