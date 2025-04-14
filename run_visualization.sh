#!/bin/bash
python web_visualize.py > visualization.log 2>&1 &
echo "Visualization server started on port 12000"
echo "Access it at: https://work-1-zwzrujpnbtpftrfq.prod-runtime.all-hands.dev/"
echo "Server logs are in visualization.log"