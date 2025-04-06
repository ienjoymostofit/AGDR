import React, { useState, useEffect, useRef, useCallback } from 'react';
import DOMPurify from 'dompurify';
import GraphVisualization from './components/Graph/GraphVisualization';
import './App.css';

// Define types for TypeScript support
interface LogEntry {
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  timestamp: string;
}

interface Entity {
  id?: string;
  name: string;
  description: string;
  category: string[];
}

interface Relationship {
  source_entity_name: string;
  target_entity_name: string;
  relation_type: string;
  attributes: Record<string, any>;
}

interface WebSocketMessage {
  type: string;
  iteration?: number;
  total_iterations?: number;
  prompt?: string;
  reasoning_trace?: string;
  entities_count?: number;
  relationships_count?: number;
  entities?: Entity[];
  relationships?: Relationship[];
  message?: string;
  timestamp?: string;
}

const MAX_LOGS = 1000; // Prevent memory leaks by limiting log entries
const MAX_ITERATIONS = 100; // Safety limit for iterations
const MIN_ITERATIONS = 1;

const App: React.FC = () => {
  // State management with proper typing
  const [prompt, setPrompt] = useState<string>('');
  const [iterations, setIterations] = useState<number>(3);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<'running' | 'completed' | 'failed' | null>(null);
  const [reasoningTrace, setReasoningTrace] = useState<string>('');
  const [entities, setEntities] = useState<Entity[]>([]);
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [currentIteration, setCurrentIteration] = useState<number>(0);
  const [totalIterations, setTotalIterations] = useState<number>(0);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const logsEndRef = useRef<HTMLDivElement | null>(null);

  // Scroll to bottom of logs
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  // Clean up WebSocket connection on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
    };
  }, []);

  // Add log message with safety limits
  const addLog = useCallback((message: string, type: 'info' | 'success' | 'warning' | 'error' = 'info') => {
    const timestamp = new Date().toLocaleTimeString();
    // Sanitize the message to prevent XSS
    const sanitizedMessage = DOMPurify.sanitize(message);
    
    setLogs(prevLogs => {
      // Limit the number of logs to prevent memory issues
      const newLogs = [...prevLogs, { message: sanitizedMessage, type, timestamp }];
      if (newLogs.length > MAX_LOGS) {
        return newLogs.slice(-MAX_LOGS);
      }
      return newLogs;
    });
  }, []);

  // Handle WebSocket connection with error handling
  const connectWebSocket = useCallback((jobId: string) => {
    try {
      // Close existing connection if any
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
      
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host || 'localhost:3000';
      const wsUrl = `${protocol}//${host}/ws/${jobId}`;
      
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        setIsConnected(true);
        addLog('WebSocket connection established', 'info');
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketMessage;
          handleWebSocketMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
          addLog(`Error parsing WebSocket message: ${(error as Error).message}`, 'error');
        }
      };
      
      ws.onclose = () => {
        setIsConnected(false);
        addLog('WebSocket connection closed', 'info');
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        addLog(`WebSocket error: Connection failed`, 'error');
        setError('WebSocket connection failed. Please try again.');
      };
      
      wsRef.current = ws;
      
      // Set up a ping interval to keep the connection alive
      const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000); // 30 seconds
      
      return () => {
        clearInterval(pingInterval);
        if (ws.readyState === WebSocket.OPEN) {
          ws.close();
        }
      };
    } catch (error) {
      console.error('Error connecting to WebSocket:', error);
      addLog(`Error connecting to WebSocket: ${(error as Error).message}`, 'error');
      setError('Failed to establish WebSocket connection. Please try again.');
      return () => {};
    }
  }, [addLog]);

  // Handle WebSocket messages with proper error handling
  const handleWebSocketMessage = useCallback((data: WebSocketMessage) => {
    try {
      switch (data.type) {
        case 'iteration_start':
          if (data.iteration !== undefined && data.total_iterations !== undefined) {
            setCurrentIteration(data.iteration);
            setTotalIterations(data.total_iterations);
            addLog(`Starting iteration ${data.iteration}/${data.total_iterations}`, 'info');
          }
          break;
          
        case 'prompt_generated':
          if (data.prompt) {
            addLog(`Generated prompt: ${data.prompt}`, 'info');
          }
          break;
          
        case 'reasoning_trace':
          if (data.reasoning_trace) {
            // Sanitize the reasoning trace to prevent XSS
            setReasoningTrace(DOMPurify.sanitize(data.reasoning_trace));
            addLog('Reasoning trace generated', 'info');
          }
          break;
          
        case 'knowledge_extracted':
          if (data.entities_count !== undefined && data.relationships_count !== undefined) {
            addLog(`Extracted ${data.entities_count} entities and ${data.relationships_count} relationships`, 'success');
          }
          break;
          
        case 'graph_updated':
          if (data.entities && data.relationships) {
            // Sanitize entity and relationship data
            const sanitizedEntities = data.entities.map(entity => ({
              ...entity,
              name: DOMPurify.sanitize(entity.name),
              description: DOMPurify.sanitize(entity.description),
              category: entity.category.map(cat => DOMPurify.sanitize(cat))
            }));
            
            const sanitizedRelationships = data.relationships.map(rel => ({
              ...rel,
              source_entity_name: DOMPurify.sanitize(rel.source_entity_name),
              target_entity_name: DOMPurify.sanitize(rel.target_entity_name),
              relation_type: DOMPurify.sanitize(rel.relation_type)
            }));
            
            setEntities(sanitizedEntities);
            setRelationships(sanitizedRelationships);
            addLog('Knowledge graph updated', 'success');
          }
          break;
          
        case 'iteration_end':
          if (data.iteration !== undefined && data.total_iterations !== undefined) {
            addLog(`Completed iteration ${data.iteration}/${data.total_iterations}`, 'info');
          }
          break;
          
        case 'job_completed':
          setJobStatus('completed');
          addLog('Knowledge graph generation completed', 'success');
          break;
          
        case 'error':
          setJobStatus('failed');
          if (data.message) {
            addLog(`Error: ${data.message}`, 'error');
            setError(data.message);
          }
          break;
          
        case 'info':
          if (data.message) {
            addLog(data.message, 'info');
          }
          break;
          
        case 'pong':
          // Handle ping response, no action needed
          break;
          
        default:
          addLog(`Unknown message type: ${data.type}`, 'warning');
      }
    } catch (error) {
      console.error('Error handling WebSocket message:', error);
      addLog(`Error handling WebSocket message: ${(error as Error).message}`, 'error');
    }
  }, [addLog]);

  // Start knowledge graph generation with proper validation and error handling
  const startGeneration = useCallback(async () => {
    // Reset error state
    setError(null);
    
    // Validate input
    if (!prompt.trim()) {
      addLog('Please enter a prompt', 'error');
      setError('Please enter a prompt');
      return;
    }
    
    // Validate iterations
    const iterationCount = parseInt(String(iterations), 10);
    if (isNaN(iterationCount) || iterationCount < MIN_ITERATIONS || iterationCount > MAX_ITERATIONS) {
      addLog(`Iterations must be between ${MIN_ITERATIONS} and ${MAX_ITERATIONS}`, 'error');
      setError(`Iterations must be between ${MIN_ITERATIONS} and ${MAX_ITERATIONS}`);
      return;
    }
    
    try {
      // Create a request with CSRF protection
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
      
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken,
        },
        body: JSON.stringify({
          prompt: prompt.trim(),
          iterations: iterationCount,
        }),
        credentials: 'same-origin', // Include cookies for session-based auth
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (!data.job_id) {
        throw new Error('Invalid response from server: missing job ID');
      }
      
      // Reset state for new job
      setJobId(data.job_id);
      setJobStatus('running');
      setCurrentIteration(0);
      setTotalIterations(iterationCount);
      setEntities([]);
      setRelationships([]);
      setReasoningTrace('');
      setLogs([]);
      setSelectedEntity(null);
      
      addLog(`Started knowledge graph generation with job ID: ${data.job_id}`, 'info');
      
      // Connect to WebSocket
      connectWebSocket(data.job_id);
    } catch (error) {
      console.error('Error starting generation:', error);
      addLog(`Error: ${(error as Error).message}`, 'error');
      setError((error as Error).message);
    }
  }, [prompt, iterations, addLog, connectWebSocket]);

  // Handle node click with proper validation
  const handleNodeClick = useCallback((node: Entity) => {
    if (node && node.name) {
      setSelectedEntity(node);
    }
  }, []);

  // Format graph data for visualization with proper validation
  const formatGraphData = useCallback(() => {
    if (!entities.length) return { nodes: [], links: [] };
    
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
  }, [entities, relationships]);

  // Handle iteration input change with validation
  const handleIterationChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    if (!isNaN(value)) {
      setIterations(Math.min(Math.max(value, MIN_ITERATIONS), MAX_ITERATIONS));
    } else {
      setIterations(MIN_ITERATIONS);
    }
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Agentic Deep Graph Reasoning</h1>
      </header>
      
      <main className="app-main">
        <div className="control-panel">
          <div className="input-section">
            <h2>Generate Knowledge Graph</h2>
            {error && (
              <div className="error-banner" role="alert">
                <p>{error}</p>
                <button 
                  className="error-close-button" 
                  onClick={() => setError(null)}
                  aria-label="Close error message"
                >
                  ×
                </button>
              </div>
            )}
            <div className="form-group">
              <label htmlFor="prompt">Prompt:</label>
              <textarea
                id="prompt"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Enter a prompt to generate a knowledge graph..."
                disabled={jobStatus === 'running'}
                aria-describedby="prompt-help"
                maxLength={5000} // Reasonable limit for prompt length
              />
              <small id="prompt-help" className="form-text">
                Enter a clear, specific prompt to generate a knowledge graph. Max 5000 characters.
              </small>
            </div>
            
            <div className="form-group">
              <label htmlFor="iterations">Iterations:</label>
              <input
                id="iterations"
                type="number"
                min={MIN_ITERATIONS}
                max={MAX_ITERATIONS}
                value={iterations}
                onChange={handleIterationChange}
                disabled={jobStatus === 'running'}
                aria-describedby="iterations-help"
              />
              <small id="iterations-help" className="form-text">
                Number of reasoning iterations (1-100). More iterations create larger graphs.
              </small>
            </div>
            
            <button
              className="generate-button"
              onClick={startGeneration}
              disabled={jobStatus === 'running' || !prompt.trim()}
              aria-busy={jobStatus === 'running'}
            >
              {jobStatus === 'running' ? 'Generating...' : 'Generate Knowledge Graph'}
            </button>
          </div>
          
          {jobStatus && (
            <div className="status-section">
              <h3>Status</h3>
              <div className={`status-badge ${jobStatus}`} role="status">
                {jobStatus.charAt(0).toUpperCase() + jobStatus.slice(1)}
              </div>
              
              {jobStatus === 'running' && (
                <div className="progress-container">
                  <div className="progress-bar" role="progressbar" aria-valuenow={(currentIteration / totalIterations) * 100} aria-valuemin={0} aria-valuemax={100}>
                    <div
                      className="progress"
                      style={{ width: `${(currentIteration / totalIterations) * 100}%` }}
                    ></div>
                  </div>
                  <span className="progress-text">
                    {currentIteration} / {totalIterations} iterations
                  </span>
                </div>
              )}
            </div>
          )}
          
          <div className="logs-section">
            <h3>Logs</h3>
            <div className="logs" role="log" aria-live="polite">
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
                    {relationships.filter(rel => rel.source_entity_name === selectedEntity.name || rel.target_entity_name === selectedEntity.name).length === 0 && (
                      <li className="no-relationships">No relationships found for this entity.</li>
                    )}
                  </ul>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
      
      <footer className="app-footer">
        <p>Agentic Deep Graph Reasoning - Inspired by the paper by Markus J. Buehler</p>
        <p className="security-notice">This application implements security best practices including input sanitization, CSP, and CSRF protection.</p>
      </footer>
    </div>
  );
};

export default App;