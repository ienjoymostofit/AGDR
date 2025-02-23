import logging
from neo4j import GraphDatabase
from typing import List, Optional
from models import Entity, Relationship

# --- Neo4j Client --- (No changes needed in Neo4jClient)
class Neo4jClient:
    """Client for interacting with the Neo4j database."""

    def __init__(self, uri: str, user: str, password: str):
        self.logger = logging.getLogger(__name__)
        self.uri = uri
        self.user = user
        self.password = password
        self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        """Closes the Neo4j driver connection."""
        if self._driver:
            self._driver.close()

    def query_node_names(self) -> List[str]:
        """Queries Neo4j for all node names."""
        def _query(tx):
            result = tx.run("MATCH (n) RETURN n.name AS name")
            return [record["name"] for record in result]

        try:
            with self._driver.session() as session:
                names = session.execute_read(_query)
                self.logger.info(f"Fetched {len(names)} node names from Neo4j.")
                self.logger.info(f"Node names: {names}")
                return names
        except Exception as e:
            self.logger.error(f"Error querying node names from Neo4j: {e}")
            return []

    def create_node(self, entity: Entity) -> Optional[str]:
        """Creates a node in Neo4j for the given entity, handling duplicates and label merging."""
        def _create_node_tx(tx, entity_data: Entity):
            category_labels = ":".join([f"`{category}`" for category in entity_data.category]) if entity_data.category else ""
            query = "MATCH (n {name: $name}) RETURN elementId(n) AS existing_node_id"
            result = tx.run(query, name=entity_data.name).single()

            if result:
                node_id = result["existing_node_id"]
                self.logger.info(f"Node with name '{entity_data.name}' already exists (ID: {node_id}). Merging labels.")
                merge_labels_query = f"MATCH (n) WHERE elementId(n) = $node_id SET n:{category_labels}"
                tx.run(merge_labels_query, node_id=node_id)
                return node_id
            else:
                create_query = f"CREATE (n:{category_labels} {{name: $name, description: $description}}) RETURN elementId(n) AS node_id"
                result = tx.run(
                    create_query, name=entity_data.name, description=entity_data.description
                ).single()
                node_id = result["node_id"]
                self.logger.info(f"Created node for '{entity_data.name}' with Neo4j ID: {node_id}")
                return node_id
        try:
            with self._driver.session() as session:
                return session.execute_write(_create_node_tx, entity)
        except Exception as e:
            self.logger.error(f"Error creating Neo4j node for entity '{entity.name}': {e}")
            return None


    def create_relationship(self, relationship: Relationship) -> None:
        """Creates a relationship in Neo4j, merging duplicates."""
        def _create_relationship_tx(tx, relationship_data: Relationship):
            if not isinstance(relationship_data.attributes, dict):
                relationship_data.attributes = {"stored_data": relationship_data.attributes}  # Fallback for non-dict attributes

            # Format the relationship type directly into the query
            rel_type = relationship_data.relation_type.replace('`', '').replace('"', '').replace("'", '')
            query = f"""
                MATCH (source) WHERE elementId(source) = $source_entity_id
                MATCH (target) WHERE elementId(target) = $target_entity_id
                MERGE (source)-[r:`{rel_type}`]->(target)
                SET r += $attributes
            """
            self.logger.debug(f"Executing Neo4j query: {query}")
            tx.run(
                query,
                source_entity_id=relationship_data.source_entity_id,
                target_entity_id=relationship_data.target_entity_id,
                attributes=relationship_data.attributes,
            )
            self.logger.info(f"Created/merged relationship: {relationship_data.relation_type} between entities {relationship_data.source_entity_id} and {relationship_data.target_entity_id}")

        try:
            with self._driver.session() as session:
                session.execute_write(_create_relationship_tx, relationship)
        except Exception as e:
            self.logger.error(f"Error creating Neo4j relationship: {e}")
