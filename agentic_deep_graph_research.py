import os
import json
import sys
import logging
from typing import List, Dict, Optional, Tuple
import openai
from dotenv import load_dotenv
from neo4j import GraphDatabase
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from models import Entity, Relationship, KnowledgeGraphData

print(f"Current working directory: {os.getcwd()}") # ADD THIS LINE

# Load environment variables
load_dotenv()

# --- Configuration ---
class ModelConfig(BaseModel):
    """Configuration for a specific OpenAI model."""
    model_name: str
    api_key: str = Field(..., validation_alias="OPENAI_API_KEY") # Still need API Key, even if potentially shared
    base_url: str # Base URL is now required here

class Settings(BaseSettings):
    """Settings for the knowledge graph generation application."""

    reasoning_model_config: ModelConfig = Field(..., validation_alias="REASONING_MODEL_CONFIG")
    entity_extraction_model_config: ModelConfig = Field(..., validation_alias="ENTITY_EXTRACTION_MODEL_CONFIG")
    neo4j_uri: str = Field(..., validation_alias="NEO4J_URI")
    neo4j_user: str = Field(..., validation_alias="NEO4J_USER")
    neo4j_password: str = Field(..., validation_alias="NEO4J_PASSWORD")

    model_config = SettingsConfigDict(env_file=".env", extra='ignore', env_file_encoding="utf-8", env_nested_delimiter='_')

settings = Settings()  # type: ignore [call-arg]

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(module)s - %(message)s"
)
logger = logging.getLogger(__name__)


# --- Neo4j Client --- (No changes needed in Neo4jClient)
class Neo4jClient:
    """Client for interacting with the Neo4j database."""

    def __init__(self, uri: str, user: str, password: str):
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
                logger.info(f"Fetched {len(names)} node names from Neo4j.")
                return names
        except Exception as e:
            logger.error(f"Error querying node names from Neo4j: {e}")
            return []

    def create_node(self, entity: Entity) -> Optional[str]:
        """Creates a node in Neo4j for the given entity, handling duplicates and label merging."""
        def _create_node_tx(tx, entity_data: Entity):
            category_labels = ":".join([f"`{category}`" for category in entity_data.category]) if entity_data.category else ""
            query = "MATCH (n {name: $name}) RETURN elementId(n) AS existing_node_id"
            result = tx.run(query, name=entity_data.name).single()

            if result:
                node_id = result["existing_node_id"]
                logger.info(f"Node with name '{entity_data.name}' already exists (ID: {node_id}). Merging labels.")
                merge_labels_query = f"MATCH (n) WHERE elementId(n) = $node_id SET n:{category_labels}"
                tx.run(merge_labels_query, node_id=node_id)
                return node_id
            else:
                create_query = f"CREATE (n:{category_labels} {{name: $name, description: $description}}) RETURN elementId(n) AS node_id"
                result = tx.run(
                    create_query, name=entity_data.name, description=entity_data.description
                ).single()
                node_id = result["node_id"]
                logger.info(f"Created node for '{entity_data.name}' with Neo4j ID: {node_id}")
                return node_id
        try:
            with self._driver.session() as session:
                return session.execute_write(_create_node_tx, entity)
        except Exception as e:
            logger.error(f"Error creating Neo4j node for entity '{entity.name}': {e}")
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
            logger.debug(f"Executing Neo4j query: {query}")
            tx.run(
                query,
                source_entity_id=relationship_data.source_entity_id,
                target_entity_id=relationship_data.target_entity_id,
                attributes=relationship_data.attributes,
            )
            logger.info(f"Created/merged relationship: {relationship_data.relation_type} between entities {relationship_data.source_entity_id} and {relationship_data.target_entity_id}")

        try:
            with self._driver.session() as session:
                session.execute_write(_create_relationship_tx, relationship)
        except Exception as e:
            logger.error(f"Error creating Neo4j relationship: {e}")

# --- OpenAI Client ---
class OpenAIClient:
    """Client for interacting with the OpenAI API, supporting multiple base URLs and API keys."""

    def generate_reasoning_trace(self, model_config: ModelConfig, prompt: str) -> Optional[str]:
        """Generates a reasoning trace from the specified language model, using provided config."""
        try:
            client = openai.OpenAI(api_key=model_config.api_key, base_url=model_config.base_url) # Instantiate client per call
            response = client.chat.completions.create(
                model=model_config.model_name, # Use model name from config
                stream=True,
                stop="</think>",
                messages=[
                    {"role": "system", "content": "You MUST always output <think> content, never leave it empty!"},
                    {"role": "user", "content": prompt},
                ],
            )
            content = ""
            for chunk in response:
                text = chunk.choices[0].delta.content
                if text:
                    print(text, end="", flush=True)  # Stream output to stdout
                    content += text
                if content.endswith("</think>"):
                    print("\nEarly stopping reasoning trace..")
                    break
            return content.strip()
        except openai.APIError as e:
            logger.error(f"OpenAI API error during reasoning trace generation: {e} - Model: {model_config.model_name}, Base URL: {model_config.base_url}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error during reasoning trace generation: {e} - Model: {model_config.model_name}, Base URL: {model_config.base_url}")
            return None

    def generate_structured_data(self, model_config: ModelConfig, prompt: str) -> Optional[KnowledgeGraphData]:
        """Generates structured knowledge graph data, using provided model config."""
        try:
            client = openai.OpenAI(api_key=model_config.api_key, base_url=model_config.base_url) # Instantiate client per call
            response = client.chat.completions.create(
                model=model_config.model_name, # Use model name from config
                stream=True,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )

            content = ""
            for chunk in response:
                text = chunk.choices[0].delta.content
                if text:
                    print(text, end="", flush=True)  # Stream output to stdout
                    content += text

            if not content:
                logger.warning(f"No content received from OpenAI for structured data generation. Model: {model_config.model_name}, Base URL: {model_config.base_url}")
                return None

            try:
                structured_data = json.loads(content)
                return KnowledgeGraphData(**structured_data)  # Pydantic validation here
            except json.JSONDecodeError as e:
                logger.error(f"JSONDecodeError: {e} - Content received: {content} - Model: {model_config.model_name}, Base URL: {model_config.base_url}")
                return None
            except ValidationError as e:
                logger.error(f"Pydantic ValidationError: {e} - Content received: {content} - Model: {model_config.model_name}, Base URL: {model_config.base_url}")
                return None

        except openai.APIError as e:
            logger.error(f"OpenAI API error during structured data generation: {e} - Model: {model_config.model_name}, Base URL: {model_config.base_url}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error during structured data generation: {e} - Model: {model_config.model_name}, Base URL: {model_config.base_url}")
            return None

    def generate_prompt(self, model_config: ModelConfig, knowledge_graph_data: KnowledgeGraphData, original_prompt: str) -> Optional[str]:
        """Generates a new prompt for reasoning based on the current knowledge graph, using provided model config."""
        prompt_text = f"""{json.dumps(knowledge_graph_data.to_dict(), indent=2)}\nFrom the knowledge graph above, generate a concise new natural language prompt for an LLM, with the intent to extend the knowledge with at least one new concept.

        The original query from the user was: "{original_prompt}"

        Formulate the new prompt as an open-ended question that encourages the model to reason and expand on the existing concepts and relationships in the graph.

        Respond exclusively with the prompt.
        """
        logger.info(f"Generating new prompt with model: {model_config.model_name}, Base URL: {model_config.base_url}")
        try:
            client = openai.OpenAI(api_key=model_config.api_key, base_url=model_config.base_url) # Instantiate client per call
            response = client.chat.completions.create(
                model=model_config.model_name, # Use model name from config
                stream=False, # No need to stream this prompt generation
                messages=[{"role": "user", "content": prompt_text}],
            )
            if response.choices[0] and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
            else:
                logger.warning(f"No content received from OpenAI for prompt generation. Model: {model_config.model_name}, Base URL: {model_config.base_url}")
                return None
        except openai.APIError as e:
            logger.error(f"OpenAI API error during prompt generation: {e} - Model: {model_config.model_name}, Base URL: {model_config.base_url}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error during prompt generation: {e} - Model: {model_config.model_name}, Base URL: {model_config.base_url}")
            return None


# --- Knowledge Graph Generation Logic ---
class KnowledgeGraphGenerator:
    """Orchestrates the knowledge graph generation process."""

    def __init__(self, openai_client: OpenAIClient, neo4j_client: Neo4jClient, settings: Settings):
        self.openai_client = openai_client
        self.neo4j_client = neo4j_client
        self.settings = settings

    def generate_knowledge_graph_data(self, reasoning_trace: str, existing_entity_names_str: str = "") -> Optional[KnowledgeGraphData]:
        """Generates structured knowledge graph data using OpenAI."""
        prompt = f"""Analyze the given content and extract all mentioned entities and relationships. Use singular MixedCase for entity names, and snake case names for relationships. Do not make up information, only refer to the content provided.

        <content>{reasoning_trace}</content>

        The following entities already exist in the knowledge graph: {existing_entity_names_str}.  Consider these existing entities when extracting new entities and relationships.

        Return a JSON object containing 'entities' and 'relationships' keys. The 'entities' key should contain an array of entities, each with 'id', 'name', 'description', and 'category' fields. The 'category' field should be a list of strings. The 'relationships' key should contain an array of relationships, each with 'source_entity_id', 'target_entity_id', 'relation_type', and 'attributes' fields.

            Example:
        {EXAMPLE_JSON_STR}
            """ # Using EXAMPLE_JSON_STR constant

        return self.openai_client.generate_structured_data(self.settings.entity_extraction_model_config, prompt) # Pass model config


    def run_kg_generation_iterations(self, initial_prompt: str, max_iterations: int):
        """Runs the knowledge graph generation process for a specified number of iterations."""
        knowledge_graph_data: Optional[KnowledgeGraphData] = None

        existing_entity_names = self.neo4j_client.query_node_names()
        existing_entity_names_str = ", ".join(existing_entity_names)

        prompt = initial_prompt
        original_prompt = initial_prompt  # Keep original prompt for context in new prompt generation

        for _ in range(max_iterations):
            if knowledge_graph_data:
                logger.info("Generating next iteration prompt...")
                prompt = self.openai_client.generate_prompt(
                    self.settings.entity_extraction_model_config, knowledge_graph_data, original_prompt # Pass model config
                )
                if not prompt:
                    logger.error("Failed to generate new prompt, stopping iterations.")
                    break
                logger.info(f"Next prompt: {prompt}")


            reasoning_trace = self.openai_client.generate_reasoning_trace(self.settings.reasoning_model_config, prompt) # Pass model config
            if not reasoning_trace:
                logger.error("Failed to generate reasoning trace, stopping iterations.")
                break

            new_knowledge_graph_data = self.generate_knowledge_graph_data(reasoning_trace, existing_entity_names_str)

            if new_knowledge_graph_data and new_knowledge_graph_data.entities:
                logger.info(f"Found {len(new_knowledge_graph_data.entities)} new entities.")
                entity_id_map: Dict[int, str] = {} # LLM entity ID (int) -> Neo4j Node ID (str)

# Process entities first and build ID mapping
                entity_id_map = {}
                for entity_data in new_knowledge_graph_data.entities:
                    # Ensure we have an Entity object
                    entity = entity_data if isinstance(entity_data, Entity) else Entity(**entity_data)
                    original_entity_id = int(entity.id)  # Store original ID before it gets updated
                    logger.info(f"Processing entity: {entity.name} (Original LLM ID: {original_entity_id})")

                    node_id = self.neo4j_client.create_node(entity)
                    if node_id:
                        entity_id_map[original_entity_id] = node_id
                        logger.info(f"Entity '{entity.name}', Original ID {original_entity_id} -> Neo4j ID: {node_id}")
                        # Update entity's ID to Neo4j ID for subsequent iterations
                        entity.id = node_id
                    else:
                        logger.warning(f"Failed to create Neo4j node for entity '{entity.name}'. Skipping relationships for this entity.")
                        continue

                logger.info(f"Current entity_id_map: {entity_id_map}")  # Debug logging

                # Process relationships using the ID mapping
                for relationship_data in new_knowledge_graph_data.relationships:
                    relationship = relationship_data if isinstance(relationship_data, Relationship) else Relationship(**relationship_data)
                    original_source_id = int(relationship.source_entity_id)
                    original_target_id = int(relationship.target_entity_id)

                    source_neo4j_id = entity_id_map.get(original_source_id)
                    target_neo4j_id = entity_id_map.get(original_target_id)

                    if source_neo4j_id and target_neo4j_id:
                        logger.info(f"Mapping relationship: Source {original_source_id}->{source_neo4j_id}, Target {original_target_id}->{target_neo4j_id}")
                        relationship.source_entity_id = source_neo4j_id
                        relationship.target_entity_id = target_neo4j_id
                        self.neo4j_client.create_relationship(relationship)
                    else:
                        logger.warning(
                            f"Skipping relationship '{relationship.relation_type}' due to missing Neo4j IDs. "
                            f"Source ID {original_source_id} -> {source_neo4j_id}, "
                            f"Target ID {original_target_id} -> {target_neo4j_id}"
                        )

                knowledge_graph_data = new_knowledge_graph_data # Update KG data for next iteration

                logger.info("\n--- Entities added in this iteration ---")
                for entity in knowledge_graph_data.entities:
                    logger.info(f"  - Name: {entity.name}, ID: {entity.id}, Categories: {entity.category}")
                logger.info("\n--- Relationships added in this iteration ---")
                for relationship in knowledge_graph_data.relationships:
                    logger.info(f"  - {relationship.relation_type} from {relationship.source_entity_id} to {relationship.target_entity_id}, Attributes: {relationship.attributes}")

            else:
                logger.info("No new entities generated in this iteration.")
                break # Stop iterations if no new entities are generated

        logger.info("Knowledge graph generation process completed.")

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


    EXAMPLE_JSON_STR = json.dumps({ # Moved Example JSON into code as constant string, could also be in config file
        "entities": [
            {"id": "1", "name": "GlassWindow", "description": "A type of material used for windows that don't break when hit hard.", "category": ["Material"]},
            {"id": "2", "name": "Airbag", "description": "A safety device in vehicles that inflate to cushion impacts.", "category": ["Product"]},
            {"id": "3", "name": "ImpactResistantMaterial", "description": "A type of material that doesn't break when hit hard.", "category": ["Material"]},
            {"id": "4", "name": "Polycarbonate", "description": "A type of plastic used in various applications.", "category": ["Material"]},
            {"id": "5", "name": "CarbonFiberComposite", "description": "A material made from fibers and resin.", "category": ["Material"]},
            {"id": "6", "name": "ThermalEffect", "description": "The reaction of a material to heat and temperature changes.", "category": ["Property"]},
            {"id": "7", "name": "Rigidity", "description": "A measure of an object's resistance to deformation under stress.", "category": ["Property"]},
            {"id": "8", "name": "Durability", "description": "The ability of a material to withstand wear and tear over time.", "category": ["Property"]},
            {"id": "9", "name": "ThermalInsulation", "description": "A property that prevents the transfer of heat through materials.", "category": ["Property"]}
        ],
        "relationships": [
            {"source_entity_id": "3", "target_entity_id": "1", "relation_type": "example_of", "attributes": {"effectiveness": "high"}},
            {"source_entity_id": "3", "target_entity_id": "2", "relation_type": "example_of", "attributes": {"reliability": "high", "cost_effectiveness": "medium"}},
            {"source_entity_id": "6", "target_entity_id": "3", "relation_type": "characteristic_of", "attributes": {"importance": "critical", "measurability": "quantifiable"}},
            {"source_entity_id": "7", "target_entity_id": "3", "relation_type": "characteristic_of", "attributes": {"strength": "high", "flexibility": "low"}},
            {"source_entity_id": "8", "target_entity_id": "3", "relation_type": "characteristic_of", "attributes": {"lifespan": "years", "maintenance_needs": "low"}},
            {"source_entity_id": "6", "target_entity_id": "9", "relation_type": "related_to", "attributes": {"correlation": "strong", "dependency": "direct"}},
            {"source_entity_id": "4", "target_entity_id": "1", "relation_type": "instance_of", "attributes": {"quality": "high", "cost": "moderate"}},
            {"source_entity_id": "5", "target_entity_id": "2", "relation_type": "instance_of", "attributes": {"strength_rating": "excellent", "weight": "light"}}
        ]
    }, indent=2)


    openai_client = OpenAIClient() # No longer needs API key and base url in constructor
    neo4j_client = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    kg_generator = KnowledgeGraphGenerator(openai_client, neo4j_client, settings)

    try:
        kg_generator.run_kg_generation_iterations(initial_prompt, max_iterations)
    except Exception as e:
        logger.exception("Unhandled exception during knowledge graph generation process.")
        print(f"An unexpected error occurred: {e}") # Still printing to stdout for critical unhandled errors for visibility
        sys.exit(2) # Different exit code for unhandled exception
    finally:
        neo4j_client.close() # Ensure Neo4j driver is closed in finally block
        logger.info("Application finished.")
