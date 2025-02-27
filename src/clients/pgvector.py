import logging
import psycopg2
import numpy as np
from pgvector.psycopg2 import register_vector
from typing import List, Tuple, Optional

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
                    description TEXT,
                    embedding vector({self.vector_dimension})
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

    def insert_embedding(self, entity_name: str, description: str, embedding: np.ndarray):
        """Inserts an embedding for an entity into the database."""
        if not self.conn:
            raise Exception("Database connection not established. Call connect() first.")
        cur = self.conn.cursor()
        try:
            cur.execute(
                f"INSERT INTO {self.table_name} (entity_name, description, embedding) VALUES (%s, %s, %s) ON CONFLICT (entity_name) DO UPDATE SET embedding = EXCLUDED.embedding, description = EXCLUDED.description",
                (entity_name, description, embedding)
            )
            self.conn.commit()
            logger.debug(f"Embedding inserted/updated for entity: {entity_name}")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error inserting embedding for entity '{entity_name}': {e}")
            raise
        finally:
            cur.close()

    def get_nearest_neighbors(self, embedding: np.ndarray, limit: int = 5) -> Optional[List[Tuple[str, str, float]]]:
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
                SELECT entity_name, description, embedding <-> %s AS distance
                FROM {self.table_name}
                ORDER BY embedding <-> %s
                LIMIT %s
                """,
                (embedding, embedding, limit)
            )
            results = []
            for record in cur.fetchall():
                entity_name, description, distance = record
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
