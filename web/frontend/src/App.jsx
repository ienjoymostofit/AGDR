import React, { useState, useEffect, useRef } from 'react';
import GraphVisualization from './components/Graph/GraphVisualization';
import './App.css';

const App = () => {
  const [prompt, setPrompt] = useState('');
  const [iterations, setIterations] = useState(3);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [reasoningTrace, setReasoningTrace] = useState('');
  const [entities, setEntities] = useState([]);
  const [relationships, setRelationships] = useState([]);
  const [currentIteration, setCurrentIteration] = useState(0);
  const [totalIterations, setTotalIterations] = useState(0);
  const [logs, setLogs] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [selectedEntity, setSelectedEntity] = useState(null);
  
  const wsRef = useRef(null);
  const logsEndRef = useRef(null);

  // Scroll to bottom of logs
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  // Handle WebSocket connection
  const connectWebSocket = (jobId) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${jobId}`;
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      setIsConnected(true);
      addLog('WebSocket connection established', 'info');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    };
    
    ws.onclose = () => {
      setIsConnected(false);
      addLog('WebSocket connection closed', 'info');
    };
    
    ws.onerror = (error) => {
      addLog(`WebSocket error: ${error}`, 'error');
    };
    
    wsRef.current = ws;
    
    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  };

  // Handle WebSocket messages
  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'iteration_start':
        setCurrentIteration(data.iteration);
        setTotalIterations(data.total_iterations);
        addLog(`Starting iteration ${data.iteration}/${data.total_iterations}`, 'info');
        break;
        
      case 'prompt_generated':
        addLog(`Generated prompt: ${data.prompt}`, 'info');
        break;
        
      case 'reasoning_trace':
        setReasoningTrace(data.reasoning_trace);
        addLog('Reasoning trace generated', 'info');
        break;
        
      case 'knowledge_extracted':
        addLog(`Extracted ${data.entities_count} entities and ${data.relationships_count} relationships`, 'success');
        break;
        
      case 'graph_updated':
        setEntities(data.entities);
        setRelationships(data.relationships);
        addLog('Knowledge graph updated', 'success');
        break;
        
      case 'iteration_end':
        addLog(`Completed iteration ${data.iteration}/${data.total_iterations}`, 'info');
        break;
        
      case 'job_completed':
        setJobStatus('completed');
        addLog('Knowledge graph generation completed', 'success');
        break;
        
      case 'error':
        setJobStatus('failed');
        addLog(`Error: ${data.message}`, 'error');
        break;
        
      case 'info':
        addLog(data.message, 'info');
        break;
        
      default:
        addLog(`Unknown message type: ${data.type}`, 'warning');
    }
  };

  // Add log message
  const addLog = (message, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prevLogs => [...prevLogs, { message, type, timestamp }]);
  };

  // Start knowledge graph generation
  const startGeneration = async () => {
    if (!prompt) {
      addLog('Please enter a prompt', 'error');
      return;
    }
    
    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt,
          iterations: parseInt(iterations, 10),
        }),
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setJobId(data.job_id);
        setJobStatus('running');
        setCurrentIteration(0);
        setTotalIterations(parseInt(iterations, 10));
        setEntities([]);
        setRelationships([]);
        setReasoningTrace('');
        setLogs([]);
        addLog(`Started knowledge graph generation with job ID: ${data.job_id}`, 'info');
        
        // Connect to WebSocket
        connectWebSocket(data.job_id);
      } else {
        addLog(`Error: ${data.detail}`, 'error');
      }
    } catch (error) {
      addLog(`Error: ${error.message}`, 'error');
    }
  };

  // Handle node click
  const handleNodeClick = (node) => {
    setSelectedEntity(node);
  };

  // Format graph data for visualization
  const formatGraphData = () => {
    const nodes = entities.map(entity => ({
      ...entity,
      id: entity.name,
    }));
    
    const links = relationships.map(rel => ({
      ...rel,
      id: `${rel.source_entity_name}-${rel.relation_type}-${rel.target_entity_name}`,
      source: rel.source_entity_name,
      target: rel.target_entity_name,
    }));
    
    return { nodes, links };
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Agentic Deep Graph Reasoning</h1>
      </header>
      
      <main className="app-main">
        <div className="control-panel">
          <div className="input-section">
            <h2>Generate Knowledge Graph</h2>
            <div className="form-group">
              <label htmlFor="prompt">Prompt:</label>
              <textarea
                id="prompt"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Enter a prompt to generate a knowledge graph..."
                disabled={jobStatus === 'running'}
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="iterations">Iterations:</label>
              <input
                id="iterations"
                type="number"
                min="1"
                max="100"
                value={iterations}
                onChange={(e) => setIterations(e.target.value)}
                disabled={jobStatus === 'running'}
              />
            </div>
            
            <button
              className="generate-button"
              onClick={startGeneration}
              disabled={jobStatus === 'running' || !prompt}
            >
              {jobStatus === 'running' ? 'Generating...' : 'Generate Knowledge Graph'}
            </button>
          </div>
          
          {jobStatus && (
            <div className="status-section">
              <h3>Status</h3>
              <div className={`status-badge ${jobStatus}`}>
                {jobStatus.charAt(0).toUpperCase() + jobStatus.slice(1)}
              </div>
              
              {jobStatus === 'running' && (
                <div className="progress-bar">
                  <div
                    className="progress"
                    style={{ width: `${(currentIteration / totalIterations) * 100}%` }}
                  ></div>
                  <span className="progress-text">
                    {currentIteration} / {totalIterations} iterations
                  </span>
                </div>
              )}
            </div>
          )}
          
          <div className="logs-section">
            <h3>Logs</h3>
            <div className="logs">
              {logs.map((log, index) => (
                <div key={index} className={`log-entry ${log.type}`}>
                  <span className="log-timestamp">{log.timestamp}</span>
                  <span className="log-message">{log.message}</span>
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          </div>
        </div>
        
        <div className="visualization-panel">
          <div className="graph-section">
            <h2>Knowledge Graph</h2>
            {entities.length > 0 ? (
              <GraphVisualization
                {...formatGraphData()}
                onNodeClick={handleNodeClick}
              />
            ) : (
              <div className="empty-graph">
                <p>No knowledge graph data available yet.</p>
                <p>Generate a knowledge graph to visualize it here.</p>
              </div>
            )}
          </div>
          
          <div className="details-panel">
            <div className="reasoning-section">
              <h3>Reasoning Trace</h3>
              <div className="reasoning-content">
                {reasoningTrace ? (
                  <pre>{reasoningTrace}</pre>
                ) : (
                  <p className="empty-message">No reasoning trace available yet.</p>
                )}
              </div>
            </div>
            
            {selectedEntity && (
              <div className="entity-details">
                <h3>Entity Details</h3>
                <div className="entity-card">
                  <h4>{selectedEntity.name}</h4>
                  <p className="entity-description">{selectedEntity.description}</p>
                  <div className="entity-categories">
                    {selectedEntity.category.map((cat, index) => (
                      <span key={index} className="category-tag">{cat}</span>
                    ))}
                  </div>
                  
                  <h5>Relationships</h5>
                  <ul className="relationships-list">
                    {relationships
                      .filter(rel => rel.source_entity_name === selectedEntity.name || rel.target_entity_name === selectedEntity.name)
                      .map((rel, index) => (
                        <li key={index} className="relationship-item">
                          {rel.source_entity_name === selectedEntity.name ? (
                            <>
                              <span className="direction">→</span>
                              <span className="relation-type">{rel.relation_type}</span>
                              <span className="entity-name">{rel.target_entity_name}</span>
                            </>
                          ) : (
                            <>
                              <span className="entity-name">{rel.source_entity_name}</span>
                              <span className="relation-type">{rel.relation_type}</span>
                              <span className="direction">→</span>
                            </>
                          )}
                        </li>
                      ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
      
      <footer className="app-footer">
        <p>Agentic Deep Graph Reasoning - Inspired by the paper by Markus J. Buehler</p>
      </footer>
    </div>
  );
};

export default App;