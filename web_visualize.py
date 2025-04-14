from neo4j import GraphDatabase
import json
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

# HTML template for visualization
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Knowledge Graph Visualization</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body { margin: 0; font-family: Arial, sans-serif; }
        #graph { width: 100%; height: 100vh; }
        .node { cursor: pointer; }
        .link { stroke: #999; stroke-opacity: 0.6; }
        .node text { font-size: 12px; }
        .tooltip {
            position: absolute;
            background-color: white;
            border: 1px solid #ddd;
            padding: 10px;
            border-radius: 5px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.3s;
        }
    </style>
</head>
<body>
    <div id="graph"></div>
    <div class="tooltip"></div>
    <script>
        // Fetch graph data
        fetch('/graph-data')
            .then(response => response.json())
            .then(data => createGraph(data));
        
        function createGraph(data) {
            const width = window.innerWidth;
            const height = window.innerHeight;
            
            // Create SVG
            const svg = d3.select("#graph")
                .append("svg")
                .attr("width", width)
                .attr("height", height);
            
            // Create tooltip
            const tooltip = d3.select(".tooltip");
            
            // Create simulation
            const simulation = d3.forceSimulation(data.nodes)
                .force("link", d3.forceLink(data.links).id(d => d.id).distance(150))
                .force("charge", d3.forceManyBody().strength(-500))
                .force("center", d3.forceCenter(width / 2, height / 2));
            
            // Create links
            const link = svg.append("g")
                .selectAll("line")
                .data(data.links)
                .enter()
                .append("line")
                .attr("class", "link")
                .attr("stroke-width", 2);
            
            // Create link labels
            const linkText = svg.append("g")
                .selectAll("text")
                .data(data.links)
                .enter()
                .append("text")
                .text(d => d.type)
                .attr("font-size", 10)
                .attr("text-anchor", "middle")
                .attr("dy", -5);
            
            // Create nodes
            const node = svg.append("g")
                .selectAll("circle")
                .data(data.nodes)
                .enter()
                .append("circle")
                .attr("class", "node")
                .attr("r", 20)
                .attr("fill", d => {
                    // Color nodes by category
                    if (d.categories.includes("Country")) return "#4285F4";
                    if (d.categories.includes("Natural Resource")) return "#34A853";
                    if (d.categories.includes("Foreign Policy")) return "#FBBC05";
                    if (d.categories.includes("Refugee Group")) return "#EA4335";
                    return "#9AA0A6";
                })
                .on("mouseover", function(event, d) {
                    tooltip.style("opacity", 1)
                        .html(`<strong>${d.id}</strong><br/>${d.description}<br/><em>${d.categories.join(", ")}</em>`)
                        .style("left", (event.pageX + 10) + "px")
                        .style("top", (event.pageY - 10) + "px");
                })
                .on("mouseout", function() {
                    tooltip.style("opacity", 0);
                })
                .call(d3.drag()
                    .on("start", dragstarted)
                    .on("drag", dragged)
                    .on("end", dragended));
            
            // Create node labels
            const nodeText = svg.append("g")
                .selectAll("text")
                .data(data.nodes)
                .enter()
                .append("text")
                .text(d => d.id)
                .attr("font-size", 12)
                .attr("text-anchor", "middle")
                .attr("dy", 30);
            
            // Update positions on simulation tick
            simulation.on("tick", () => {
                link
                    .attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);
                
                linkText
                    .attr("x", d => (d.source.x + d.target.x) / 2)
                    .attr("y", d => (d.source.y + d.target.y) / 2);
                
                node
                    .attr("cx", d => d.x)
                    .attr("cy", d => d.y);
                
                nodeText
                    .attr("x", d => d.x)
                    .attr("y", d => d.y);
            });
            
            // Drag functions
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
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/graph-data')
def graph_data():
    # Connect to Neo4j
    driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'testtest'))
    
    nodes = []
    links = []
    
    # Query nodes and relationships
    with driver.session() as session:
        # Get all nodes
        result = session.run('MATCH (n) RETURN n.name, n.description, labels(n)')
        for record in result:
            nodes.append({
                'id': record['n.name'],
                'description': record['n.description'],
                'categories': record['labels(n)']
            })
        
        # Get all relationships
        result = session.run('MATCH (a)-[r]->(b) RETURN a.name, type(r), b.name, properties(r)')
        for record in result:
            links.append({
                'source': record['a.name'],
                'target': record['b.name'],
                'type': record['type(r)'],
                'properties': record['properties(r)']
            })
    
    # Close the driver
    driver.close()
    
    return jsonify({'nodes': nodes, 'links': links})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=12000, debug=True)