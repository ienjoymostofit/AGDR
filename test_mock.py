import os
import sys
import json

# Add src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from clients.mock_openai import MockOpenAIClient
from core.config import ModelConfig

# Create a mock model config
model_config = ModelConfig(
    model_name="mock-model",
    api_key="mock-api-key",
    base_url="mock-base-url",
    prefix_message=""
)

# Create a mock OpenAI client
mock_client = MockOpenAIClient(
    think_tags=("<thinking>", "</thinking>"),
    reasoning_model_config=model_config,
    entity_extraction_model_config=model_config,
    conflict_resolution_model_config=model_config
)

# Test with a prompt about Ancient Egypt
prompt = "Tell me about Ancient Egypt and the construction of the pyramids."
print(f"Testing with prompt: {prompt}")

# Generate reasoning trace
reasoning_trace = mock_client.generate_reasoning_trace(prompt)
print("\nReasoning trace generated successfully.")

# Extract knowledge graph
kg = mock_client.extract_knowledge_graph(reasoning_trace)
print("\nKnowledge graph extracted successfully.")

# Print the entities and relationships
print("\nEntities:")
for entity in kg.entities:
    print(f"- {entity.name}: {entity.description}")

print("\nRelationships:")
for rel in kg.relationships:
    print(f"- {rel.source_entity_name} {rel.relation_type} {rel.target_entity_name}")