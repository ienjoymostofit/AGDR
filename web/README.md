# Agentic Deep Graph Reasoning Web Interface

This directory contains the web interface for the Agentic Deep Graph Reasoning project, providing a user-friendly way to interact with the knowledge graph generation system.

## Architecture

The web interface consists of two main components:

1. **Backend**: A FastAPI application that provides a REST API and WebSocket server for real-time updates
2. **Frontend**: A React application that provides a user interface for interacting with the system

## Features

- **Interactive Knowledge Graph Visualization**: Visualize the knowledge graph as it's being constructed
- **Real-time Reasoning Display**: See the reasoning process in real-time
- **User-friendly Interface**: Easy-to-use interface for submitting prompts and configuring parameters
- **Entity Details**: View detailed information about entities and their relationships
- **Progress Tracking**: Track the progress of knowledge graph generation

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js 16+ (for local development)
- Python 3.8+ (for local development)

### Running with Docker Compose

1. Make sure you have the `.env` file in the root directory with the necessary environment variables
2. Run the following command from the `web` directory:

```bash
docker-compose up
```

3. Access the web interface at http://localhost:3000

### Local Development

#### Backend

1. Navigate to the `web/backend` directory
2. Install the dependencies:

```bash
pip install -r requirements.txt
```

3. Run the backend server:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

1. Navigate to the `web/frontend` directory
2. Install the dependencies:

```bash
npm install
```

3. Run the frontend development server:

```bash
npm start
```

4. Access the web interface at http://localhost:3000

## API Endpoints

### REST API

- `POST /api/generate`: Start a knowledge graph generation job
- `GET /api/jobs/{job_id}`: Get the status of a knowledge graph generation job

### WebSocket API

- `ws://localhost:8000/ws/{job_id}`: WebSocket endpoint for real-time updates on knowledge graph generation

## Directory Structure

```
web/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── Dockerfile           # Backend Dockerfile
│   └── requirements.txt     # Backend dependencies
├── frontend/
│   ├── public/              # Static files
│   ├── src/                 # React application source code
│   │   ├── components/      # React components
│   │   │   └── Graph/       # Graph visualization components
│   │   ├── App.jsx          # Main application component
│   │   └── App.css          # Application styles
│   ├── Dockerfile           # Frontend Dockerfile
│   └── package.json         # Frontend dependencies
├── docker-compose.yml       # Docker Compose configuration
└── README.md                # This file
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.