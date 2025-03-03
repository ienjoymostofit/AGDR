# Agentic Deep Graph Reasoning

This repository contains an implementation inspired by concepts from ["Agentic Deep Graph Reasoning"](https://arxiv.org/abs/2502.13025) by [Markus J. Buehler](https://orcid.org/0000-0002-4173-9659). This implementation focuses on core concepts of iterative knowledge graph expansion through language model-driven reasoning.

> [!IMPORTANT]
>  ⚠️ **Note:** This implementation has been significantly updated since the previous version. Key changes include the addition of vector embedding using pgvector for enhanced similarity comparisons and conflict resolution, a dedicated conflict resolution service, and improved model configuration options.  See the "Key Features" and "Technical Architecture" sections for more details.  Please review the updated installation and configuration instructions carefully.


## 📝 Scope Note

This is an implementation that focuses on basic autonomous knowledge graph expansion and implements core concepts of iterative reasoning and structured knowledge extraction. It provides a practical starting point for experimenting with agentic knowledge graphs.

Key characteristics:
- Focuses on autonomous knowledge graph expansion
- Implements iterative reasoning and structured knowledge extraction
- Provides a practical starting point

## 🌟 Key Features

- **Iterative Graph Expansion**: Grows knowledge graphs through recursive reasoning, exploring related concepts over multiple iterations.
- **Multi-Model Architecture**:  Leverages separate language models for reasoning, entity extraction, and conflict resolution, each configurable for optimal performance.
- **Neo4j Integration**: Provides persistent storage and querying of the generated knowledge graph using Neo4j.
- **Streaming Output**: Displays the reasoning process in real-time, providing insights into the knowledge graph generation.
- **Flexible Model Configuration**: Supports different LLM providers through configurable API endpoints, including OpenAI and local models via Ollama.
- **Vector Embedding**: Implements vector embeddings using pgvector for semantic similarity comparisons and conflict resolution.
- **Conflict Resolution**:  Addresses potential conflicts between existing and new entities using an LLM-driven conflict resolution service.

## Examples

**Prompt:** "Describe the role and stance of Sweden during World War II"

**Iterations:** 2

![Sweden during WW2, 2 iterations](images/SwedenWW2_2_Iterations_thumb.png)[Large version of image](images/SwedenWW2_2_Iterations.png)


**Prompt:** "Describe a way to design impact resistant materials"

**Iterations:** 100+

![Large Knowledge Graph](images/LargeGraph.thumb.png)[Large version of image](images/LargeGraph.png)

## 🔧 Technical Architecture

The system consists of several key components:

1.  **Reasoning Service**: Generates detailed reasoning traces about a given topic using a configured language model.
2.  **Knowledge Extractor Service**: Converts unstructured reasoning into graph-structured data (entities and relationships) based on a defined prompt.
3.  **Graph Population Service**: Handles Neo4j database operations, including creating nodes and relationships, and manages potential conflicts.
4.  **Embedding Service**: Provides vector embeddings for entities, enabling similarity searches and conflict resolution.
5.  **Conflict Resolution Service**: Resolves conflicts between existing and new entities using an LLM.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Docker and Docker Compose (for Neo4j and pgvector)
- Access to OpenAI API or a compatible LLM API endpoint (e.g., Ollama).
- A running PostgreSQL instance with the `pgvector` extension enabled.
- Access to a local LLM API endpoint (e.g., Ollama) is recommended for faster iteration, especially for the reasoning and embedding models.

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/agentic-deep-graph-reasoning.git
cd agentic-deep-graph-reasoning
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start Neo4j and pgvector using Docker Compose:
```bash
docker-compose up -d   # Only start Neo4j
```

4.  **Set up PostgreSQL with pgvector:**

    *   If you don't have a PostgreSQL instance, you can use Docker:

        ```bash
        docker-compose up -d postgres
        ```

    *   Connect to the PostgreSQL instance (e.g., using `psql`):

        ```bash
        psql -h localhost -P54321 -U postgres -d postgres
        ```

    *   Create the `pgvector` extension:

        ```sql
        CREATE EXTENSION vector;
        ```

### Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Configure your environment variables in `.env`:

```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=testtest

# Reasoning Model Configuration
REASONING_MODEL_CONFIG='{"model_name": "openthinker:7b-q8_0", "api_key": "dummy", "base_url": "http://localhost:11434/v1/", "prefix_message": ""}'

# Entity Extraction Model Configuration
ENTITY_EXTRACTION_MODEL_CONFIG='{"model_name": "gpt-4o-mini", "api_key": "sk---", "base_url": "https://api.openai.com/v1/", "prefix_message": ""}'

# Embedding Model Configuration
EMBEDDING_MODEL_CONFIG='{"model_name": "granite-embedding:30m-en-fp16", "api_key": "dummy", "base_url": "http://localhost:11434/v1/", "prefix_message": ""}'

# Conflict Resolution Model Configuration
CONFLICT_RESOLUTION_MODEL_CONFIG='{"model_name": "gpt-4o-mini", "api_key": "sk---", "base_url": "https://api.openai.com/v1/", "prefix_message": ""}'

# Reasoning Tag Configuration.  These tags are used to extract the reasoning trace from the LLM output.
# For deepscaler models:
#THINK_TAGS="[\"<think>\",\"</think>\"]"
# For openthinker models:
THINK_TAGS="[\"<|begin_of_thought|>\",\"<|end_of_thought|>\"]"

# PgVector Configuration
PGVECTOR_DBNAME=postgres
PGVECTOR_USER=postgres
PGVECTOR_PASSWORD=postgres
PGVECTOR_HOST=localhost
PGVECTOR_PORT=54321
PGVECTOR_TABLE_NAME=entity_embeddings
PGVECTOR_VECTOR_DIMENSION=1536  # optional
```

#### Model Configuration Options

- For OpenAI models:
  - `base_url`: "https://api.openai.com/v1/"
  - `model_name`: "gpt-4", "gpt-3.5-turbo", "gpt-4o-mini", etc.
  - `api_key`: Your OpenAI API key.
  - `prefix_message`: Optional message to prepend to the prompt.

- For local models (e.g., Ollama):
  - `base_url`: "http://localhost:11434/v1/"
  - `model_name`: The name of the model you have pulled from Ollama (e.g., "llama2", "mistral", "openthinker:7b-q8_0", "granite-embedding:30m-en-fp16", etc.).
  - `api_key`:  A dummy value like "dummy" can be used.
  - `prefix_message`: Optional message to prepend to the prompt.

**Important notes on model configuration:**

*   The `REASONING_MODEL_CONFIG`, `ENTITY_EXTRACTION_MODEL_CONFIG`, and `CONFLICT_RESOLUTION_MODEL_CONFIG` settings define which models are used for reasoning, entity extraction, and conflict resolution, respectively. You can use different models for these tasks.
*   The `EMBEDDING_MODEL_CONFIG` specifies the model used for generating text embeddings.
*   Different models may require different reasoning tag formats. Ensure that the `THINK_TAGS` setting is correctly configured to match the output format of your reasoning model. Refer to the model's documentation for the correct tags. Some example configurations are provided in the `.env.example` file.
*   The `prefix_message` field in the model configurations allows you to prepend a message to the prompt. This can be useful for models that require a specific prefix to function correctly.

### Reasoning Trace Format

This implementation expects the reasoning model to output its reasoning within the tags specified in the `THINK_TAGS` environment variable. This format is particularly suited for models that are trained to provide structured reasoning traces.

Example expected output for `openthinker:7b-q8_0`:
```
<|begin_of_thought|>
Okay, so I need to figure out the ...
Now, thinking about ...
<|end_of_thought|>
```

When using custom models or different LLM providers, ensure they:
1.  Always wrap reasoning in the configured tags.
2.  Provide structured, step-by-step reasoning.
3.  End the reasoning trace with the closing tag.

The system uses these tags to properly parse and process the reasoning trace for knowledge extraction. If your model doesn't natively support this format, you may need to modify the system prompt or post-process the output.

### Running the Application

Run the knowledge graph generation with:
```bash
python src/application.py "Your initial prompt" <number-of-iterations>
```

Example:
```bash
python src/application.py "Describe a way to design impact resistant materials" 3
```

## 📖 Example Prompts

- "Describe a way to design impact resistant materials"
- "Describe the role and stance of Sweden during World War II"
- "Explain how photosynthesis works in plants"

## ⚙️ Utilities

The `utilities` directory contains helpful scripts:

*   `extract_to_dot.py`: Exports the knowledge graph from Neo4j to a `.dot` file for visualization using Graphviz.
*   `re_embed_pgvector.py`: Re-embeds all entities in the pgvector database.  Useful after changing the embedding model.

## 🎯 Core Innovation

Unlike traditional knowledge graph systems, this implementation follows an agentic approach where the system:

- Autonomously determines what knowledge to expand.
- Maintains contextual awareness across iterations.
- Structures knowledge organically through reasoning.

## 🔍 Monitoring and Debugging

- Check Neo4j browser interface at `http://localhost:7474`
- View logging output in real-time during execution in the console.
- Monitor entity and relationship creation in the console output.
- Examine the generated knowledge graph in Neo4j to verify the accuracy and completeness of the extracted information.
- Monitor pgvector database for embeddings.

## 🤝 Contributing

Contributions are welcome!

## 📚 Citation

If you use this implementation in your research, please cite the original paper:

```bibtex
@article{deepgraphreasoning2025,
  title={Agentic Deep Graph Reasoning},
  author={[Markus J. Buehler]},
  journal={arXiv preprint arXiv:2502.13025},
  year={2025}
}
```
```
