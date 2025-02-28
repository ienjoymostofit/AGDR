import logging
import psycopg2
import numpy as np
from pgvector.psycopg2 import register_vector
from typing import List, Tuple, Optional

from core.models import Entity

logger = logging.getLogger(__name__)

class PgVectorClient:
    """Client for interacting with PostgreSQL with pgvector extension."""

    def __init__(self, dbname, user, password, host, port, table_name="entity_embeddings", vector_dimension=1536):
        """
        Initializes the PgVector client with database connection details.
        """
        self.dbname = dbname
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.conn = None
        self.table_name = table_name
        self.vector_dimension = vector_dimension # Assuming embeddings from OpenAI ada model

    def is_connected(self) -> bool:
        """Returns True if the database connection is established."""
        return self.conn is not None

    def connect(self):
        """Establishes a connection to the PostgreSQL database."""
        try:
            self.conn = psycopg2.connect(dbname=self.dbname, user=self.user, password=self.password, host=self.host, port=self.port)
            register_vector(self.conn) # Register pgvector with psycopg2
            logger.info("Successfully connected to PostgreSQL with pgvector.")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            if self.conn:
                self.close()
            raise

    def create_extension(self):
        """Creates the pgvector extension in the database if it doesn't exist."""
        if not self.conn:
            raise Exception("Database connection not established. Call connect() first.")
        cur = self.conn.cursor()
        try:
            cur.execute('CREATE EXTENSION IF NOT EXISTS vector')
            self.conn.commit()
            logger.info("pgvector extension created or already exists.")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error creating pgvector extension: {e}")
            raise
        finally:
            cur.close()

    def create_table(self):
        """Creates the embeddings table if it doesn't exist."""
        if not self.conn:
            raise Exception("Database connection not established. Call connect() first.")
        cur = self.conn.cursor()
        try:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id bigserial PRIMARY KEY,
                    entity_name TEXT UNIQUE,
                    entity_name_embedding vector({self.vector_dimension}),
                    description TEXT,
                    description_embedding vector({self.vector_dimension})
                )
            """)
            self.conn.commit()
            logger.info(f"Table '{self.table_name}' created or already exists.")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error creating table '{self.table_name}': {e}")
            raise
        finally:
            cur.close()

    def get_entities_from_last_id(self, last_id: int, limit: int) -> Optional[List[Entity]]:
        """
        Retrieves entities from the table starting from the last_id.

        Returns a list of tuples, where each tuple contains (id, entity_name, description).
        """
        if not self.conn:
            raise Exception("Database connection not established. Call connect() first.")
        cur = self.conn.cursor()
        try:
            cur.execute(f"SELECT id, entity_name, description FROM {self.table_name} WHERE id > %s ORDER BY id LIMIT %s", (last_id, limit))
            results = []
            for record in cur.fetchall():
                results.append(Entity(id=str(record[0]),name=record[1],description=record[2]))
            logger.debug(f"Entities retrieved. Count: {len(results)}")
            return results
        except Exception as e:
            logger.error(f"Error retrieving entities: {e}")
            return None
        finally:
            cur.close()

    def delete_embedding(self, entity_name: str):
        """Deletes an embedding for an entity from the database."""
        if not self.conn:
            raise Exception("Database connection not established. Call connect() first.")
        cur = self.conn.cursor()
        try:
            cur.execute(f"DELETE FROM {self.table_name} WHERE entity_name = %s", (entity_name,))
            self.conn.commit()
            logger.debug(f"Embedding deleted for entity: {entity_name}")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error deleting embedding for entity '{entity_name}': {e}")
            raise
        finally:
            cur.close()

    def insert_embedding(self, entity_name: str, entity_name_embedding: np.ndarray, description: str, description_embedding: np.ndarray):
        """Inserts an embedding for an entity into the database."""
        if not self.conn:
            raise Exception("Database connection not established. Call connect() first.")
        cur = self.conn.cursor()
        try:
            cur.execute(
                f"INSERT INTO {self.table_name} (entity_name, entity_name_embedding, description, description_embedding) VALUES (%s, %s, %s, %s) ON CONFLICT (entity_name) DO UPDATE SET entity_name_embedding = EXCLUDED.entity_name_embedding, description = EXCLUDED.description, description_embedding = EXCLUDED.description_embedding",
                (entity_name, entity_name_embedding, description, description_embedding)
            )
            self.conn.commit()
            logger.debug(f"Embedding inserted/updated for entity: {entity_name}")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error inserting embedding for entity '{entity_name}': {e}")
            raise
        finally:
            cur.close()

    def get_nearest_neighbors_by_entity_name(self, entity_name_embedding: np.ndarray, limit: int = 5) -> Optional[List[Tuple[str, str, float]]]:
        """
        Retrieves the nearest neighbors to a given entity_name.

        Returns a list of tuples, where each tuple contains (entity_name, description, distance).
        """
        if not self.conn:
            raise Exception("Database connection not established. Call connect() first.")
        cur = self.conn.cursor()
        try:
            cur.execute(
                f"""
                SELECT entity_name, description, entity_name_embedding <=> %s AS distance
                FROM {self.table_name}
                WHERE entity_name_embedding != %s
                ORDER BY entity_name_embedding <=> %s
                LIMIT %s
                """,
                (entity_name_embedding, entity_name_embedding, entity_name_embedding, limit)
            )
            results = []
            for record in cur.fetchall():
                entity_name, description, distance = record
                distance = 1.0 - distance # Convert cosine distance to similarity
                results.append((entity_name, description, distance))
            logger.debug(f"Nearest neighbors retrieved. Count: {len(results)}")
            return results
        except Exception as e:
            logger.error(f"Error retrieving nearest neighbors: {e}")
            return None
        finally:
            cur.close


    def get_nearest_neighbors_by_description(self, embedding: np.ndarray, limit: int = 5) -> Optional[List[Tuple[str, str, float]]]:
        """
        Retrieves the nearest neighbors to a given embedding vector.

        Returns a list of tuples, where each tuple contains (entity_name, description, distance).
        """
        if not self.conn:
            raise Exception("Database connection not established. Call connect() first.")
        cur = self.conn.cursor()
        try:
            cur.execute(
                f"""
                SELECT entity_name, entity_name_embedding, description, description_embedding <=> %s AS distance
                FROM {self.table_name}
                WHERE description_embedding != %s
                ORDER BY description_embedding <=> %s
                LIMIT %s
                """,
                (embedding, embedding, embedding, limit)
            )
            results = []
            for record in cur.fetchall():
                entity_name, description, distance = record
                distance = 1.0 - distance # Convert cosine distance to similarity
                results.append((entity_name, description, distance))
            logger.debug(f"Nearest neighbors retrieved. Count: {len(results)}")
            return results
        except Exception as e:
            logger.error(f"Error retrieving nearest neighbors: {e}")
            return None
        finally:
            cur.close()


    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("PostgreSQL connection closed.")
        else:
            logger.warning("PostgreSQL connection already closed or not initialized.")
