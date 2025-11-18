#!/bin/bash

SCHEME=${1:-ecmp}
SCENARIO=${2:-incast}

echo "Running experiment: $SCHEME with $SCENARIO scenario"

# Start Mininet topology
sudo python topology/leaf_spine.py &
TOPO_PID=$!

sleep 5

# Start controller
python controller/${SCHEME}_controller.py &
CTRL_PID=$!

sleep 2

# Run traffic scenario
python experiments/${SCENARIO}_test.py

# Cleanup
kill $CTRL_PID $TOPO_PID

echo "Experiment complete. Results in results/"
