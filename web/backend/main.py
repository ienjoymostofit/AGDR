from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import json
import asyncio
import logging
import os
import sys
from datetime import datetime

# Add the src directory to the path so we can import the core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from core.config import Settings
from core.factory import ServiceFactory

# Models
class GraphGenerationRequest(BaseModel):
    prompt: str
    iterations: int = 3
    model_config: Optional[Dict[str, Any]] = None

class GraphGenerationResponse(BaseModel):
    job_id: str
    status: str

# Setup FastAPI app
app = FastAPI(
    title="Agentic Deep Graph Reasoning API",
    description="API for interacting with the Agentic Deep Graph Reasoning system",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.logger = logging.getLogger(__name__)

    async def connect(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        self.active_connections[job_id] = websocket
        self.logger.info(f"WebSocket connection established for job {job_id}")

    def disconnect(self, job_id: str):
        if job_id in self.active_connections:
            del self.active_connections[job_id]
            self.logger.info(f"WebSocket connection closed for job {job_id}")

    async def send_update(self, job_id: str, data: dict):
        if job_id in self.active_connections:
            await self.active_connections[job_id].send_json(data)
            self.logger.debug(f"Sent update to job {job_id}: {data}")

manager = ConnectionManager()

# Active jobs
active_jobs = {}

# Custom KnowledgeGraphGenerator wrapper for WebSocket updates
class WebSocketKnowledgeGraphGenerator:
    def __init__(self, kg_generator, job_id):
        self.kg_generator = kg_generator
        self.job_id = job_id
        self.logger = logging.getLogger(__name__)

    async def run_kg_generation_iterations(self, initial_prompt, max_iterations):
        """
        Runs the knowledge graph generation process with WebSocket updates.
        """
        prompt = initial_prompt
        previous_node_name = None

        for i in range(max_iterations):
            # Send iteration start update
            await manager.send_update(self.job_id, {
                "type": "iteration_start",
                "iteration": i + 1,
                "total_iterations": max_iterations,
                "timestamp": datetime.now().isoformat()
            })

            # Find potential paths to explore
            longest_paths = self.kg_generator.entity_service.find_longest_shortest_paths()

            # Generate a new prompt based on the paths, if available
            if longest_paths and len(longest_paths) > 0:
                prompt = self.kg_generator._generate_next_prompt(longest_paths, previous_node_name)
                if prompt == previous_node_name:
                    prompt = f"Expanding on the concept of {prompt}, what deeper insights and connections could we explore?"
                previous_node_name = prompt.split("(")[0].strip() if "(" in prompt else prompt
                
                # Send prompt update
                await manager.send_update(self.job_id, {
                    "type": "prompt_generated",
                    "prompt": prompt,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                # Send prompt update (using initial prompt)
                await manager.send_update(self.job_id, {
                    "type": "prompt_generated",
                    "prompt": prompt,
                    "timestamp": datetime.now().isoformat()
                })

            # Generate reasoning trace
            reasoning_trace = self.kg_generator.reasoning_service.generate_reasoning_trace(prompt)
            if not reasoning_trace:
                await manager.send_update(self.job_id, {
                    "type": "error",
                    "message": "Failed to generate reasoning trace",
                    "timestamp": datetime.now().isoformat()
                })
                break

            # Send reasoning trace update
            await manager.send_update(self.job_id, {
                "type": "reasoning_trace",
                "reasoning_trace": reasoning_trace,
                "timestamp": datetime.now().isoformat()
            })

            # Extract knowledge graph from reasoning trace
            knowledge_graph_data = self.kg_generator.knowledge_extractor.extract_knowledge_graph(reasoning_trace)

            if knowledge_graph_data and knowledge_graph_data.entities:
                # Send knowledge graph update
                await manager.send_update(self.job_id, {
                    "type": "knowledge_extracted",
                    "entities_count": len(knowledge_graph_data.entities),
                    "relationships_count": len(knowledge_graph_data.relationships),
                    "timestamp": datetime.now().isoformat()
                })

                # Merge the new knowledge into the existing graph
                updated_kg = self.kg_generator.graph_populator.merge_knowledge_graph(knowledge_graph_data)

                # Send graph update
                await manager.send_update(self.job_id, {
                    "type": "graph_updated",
                    "entities": [entity.model_dump() for entity in updated_kg.entities],
                    "relationships": [rel.model_dump() for rel in updated_kg.relationships],
                    "timestamp": datetime.now().isoformat()
                })
            else:
                await manager.send_update(self.job_id, {
                    "type": "info",
                    "message": "No new entities extracted in this iteration",
                    "timestamp": datetime.now().isoformat()
                })

            # Send iteration end update
            await manager.send_update(self.job_id, {
                "type": "iteration_end",
                "iteration": i + 1,
                "total_iterations": max_iterations,
                "timestamp": datetime.now().isoformat()
            })

        # Send job completion update
        await manager.send_update(self.job_id, {
            "type": "job_completed",
            "timestamp": datetime.now().isoformat()
        })

# Initialize settings and service factory
@app.on_event("startup")
async def startup_event():
    app.state.settings = Settings()
    app.state.service_factory = ServiceFactory(app.state.settings)
    logging.info("Application started")

@app.on_event("shutdown")
async def shutdown_event():
    app.state.service_factory.close_all()
    logging.info("Application shutdown")

# API endpoints
@app.post("/api/generate", response_model=GraphGenerationResponse)
async def generate_knowledge_graph(request: GraphGenerationRequest):
    """
    Generate a knowledge graph based on the provided prompt and parameters.
    Returns a job ID that can be used to track progress via WebSocket.
    """
    try:
        # Generate a unique job ID
        job_id = f"job_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Get the knowledge graph generator
        kg_generator = app.state.service_factory.get_knowledge_graph_generator()
        
        # Create a WebSocket wrapper
        ws_kg_generator = WebSocketKnowledgeGraphGenerator(kg_generator, job_id)
        
        # Store the job
        active_jobs[job_id] = {
            "prompt": request.prompt,
            "iterations": request.iterations,
            "status": "pending",
            "generator": ws_kg_generator
        }
        
        # Start the generation process in a background task
        asyncio.create_task(start_generation_job(job_id, request.prompt, request.iterations))
        
        return {"job_id": job_id, "status": "started"}
    except Exception as e:
        logging.exception("Failed to start knowledge graph generation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start knowledge graph generation: {str(e)}"
        )

async def start_generation_job(job_id: str, prompt: str, iterations: int):
    """Background task to run the knowledge graph generation process."""
    try:
        active_jobs[job_id]["status"] = "running"
        await active_jobs[job_id]["generator"].run_kg_generation_iterations(prompt, iterations)
        active_jobs[job_id]["status"] = "completed"
    except Exception as e:
        logging.exception(f"Error in generation job {job_id}")
        active_jobs[job_id]["status"] = "failed"
        active_jobs[job_id]["error"] = str(e)
        await manager.send_update(job_id, {
            "type": "error",
            "message": f"Job failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of a knowledge graph generation job."""
    if job_id not in active_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    job = active_jobs[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "prompt": job["prompt"],
        "iterations": job["iterations"],
        "error": job.get("error")
    }

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time updates on knowledge graph generation."""
    await manager.connect(websocket, job_id)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(job_id)

# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)