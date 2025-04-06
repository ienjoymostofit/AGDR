import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import './GraphVisualization.css';

const GraphVisualization = ({ nodes, links, onNodeClick }) => {
  const svgRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // Color scale for node categories
  const categoryColorScale = d3.scaleOrdinal(d3.schemeCategory10);

  // Drag functionality
  const drag = (simulation) => {
    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }
    
    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }
    
    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }
    
    return d3.drag()
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended);
  };

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      const container = svgRef.current.parentElement;
      setDimensions({
        width: container.clientWidth,
        height: container.clientHeight
      });
    };

    window.addEventListener('resize', handleResize);
    handleResize(); // Initial sizing

    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Create and update the visualization
  useEffect(() => {
    if (!nodes || !links || nodes.length === 0) return;

    const { width, height } = dimensions;

    // Clear previous visualization
    d3.select(svgRef.current).selectAll("*").remove();

    // Create SVG
    const svg = d3.select(svgRef.current)
      .attr("width", width)
      .attr("height", height)
      .attr("viewBox", [0, 0, width, height]);

    // Add zoom functionality
    const g = svg.append("g");
    svg.call(d3.zoom()
      .extent([[0, 0], [width, height]])
      .scaleExtent([0.1, 8])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      }));

    // Create force simulation
    const simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id(d => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("x", d3.forceX(width / 2).strength(0.1))
      .force("y", d3.forceY(height / 2).strength(0.1));

    // Create links
    const link = g.append("g")
      .attr("class", "links")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", "#999")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", 2);

    // Create link labels
    const linkLabel = g.append("g")
      .attr("class", "link-labels")
      .selectAll("text")
      .data(links)
      .join("text")
      .attr("class", "link-label")
      .attr("font-size", 10)
      .attr("text-anchor", "middle")
      .text(d => d.relation_type);

    // Create nodes
    const node = g.append("g")
      .attr("class", "nodes")
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", 10)
      .attr("fill", d => categoryColorScale(d.category[0] || "Unknown"))
      .call(drag(simulation))
      .on("click", (event, d) => onNodeClick && onNodeClick(d));

    // Add node labels
    const nodeLabel = g.append("g")
      .attr("class", "node-labels")
      .selectAll("text")
      .data(nodes)
      .join("text")
      .attr("class", "node-label")
      .attr("font-size", 12)
      .attr("dx", 15)
      .attr("dy", 4)
      .text(d => d.name);

    // Add tooltips
    node.append("title")
      .text(d => `${d.name}\n${d.description}`);

    // Update positions on simulation tick
    simulation.on("tick", () => {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

      linkLabel
        .attr("x", d => (d.source.x + d.target.x) / 2)
        .attr("y", d => (d.source.y + d.target.y) / 2);

      node
        .attr("cx", d => d.x)
        .attr("cy", d => d.y);

      nodeLabel
        .attr("x", d => d.x)
        .attr("y", d => d.y);
    });

    // Cleanup
    return () => {
      simulation.stop();
    };
  }, [nodes, links, dimensions, onNodeClick]);

  return (
    <div className="graph-container">
      <svg ref={svgRef} className="graph-visualization"></svg>
    </div>
  );
};

export default GraphVisualization;