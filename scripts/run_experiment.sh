#!/bin/bash

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="../logs"
RESULTS_DIR="../results"

echo "=== Running All Experiments (Timestamp: $TIMESTAMP) ==="

# Ensure directories exist
mkdir -p "$LOG_DIR" "$RESULTS_DIR"

# Build P4 programs
echo "Building P4 programs..."
./build_all.sh

# Test 1: ECMP Incast
echo -e "\n=== Test 1: ECMP Incast ==="
python ../experiments/incast_test.py --config ../configs/experiment_config.json \
    > "$LOG_DIR/ecmp_incast_$TIMESTAMP.log" 2>&1

# Test 2: HULA Incast
echo -e "\n=== Test 2: HULA Incast ==="
python ../experiments/incast_test.py --config ../configs/experiment_config.json \
    > "$LOG_DIR/hula_incast_$TIMESTAMP.log" 2>&1

# Test 3: Microburst
echo -e "\n=== Test 3: Microburst ==="
python ../experiments/microburst_test.py --config ../configs/experiment_config.json \
    > "$LOG_DIR/microburst_$TIMESTAMP.log" 2>&1

# Test 4: Link Failure
echo -e "\n=== Test 4: Link Failure ==="
python ../experiments/link_failure_test.py --config ../configs/experiment_config.json \
    > "$LOG_DIR/link_failure_$TIMESTAMP.log" 2>&1

echo -e "\n=== All experiments complete! ==="
echo "Logs saved to: $LOG_DIR"
echo "Results saved to: $RESULTS_DIR"

# Generate plots
echo -e "\n=== Generating plots ==="
python ../analysis/plot_results.py --all

echo -e "\n✓ Done!"
