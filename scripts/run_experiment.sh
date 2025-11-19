#!/bin/bash

set -e

# ---------------------------------------------------------------------------
# Resolve project root and useful paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="$ROOT_DIR/logs"
RESULTS_DIR="$ROOT_DIR/results"

echo "=== Running All Experiments (Timestamp: $TIMESTAMP) ==="

# Ensure directories exist
mkdir -p "$LOG_DIR" "$RESULTS_DIR"

# ---------------------------------------------------------------------------
# Build P4 programs (ECMP + HULA)
# ---------------------------------------------------------------------------
echo "Building P4 programs..."
bash "$SCRIPT_DIR/build_all.sh"

# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------

# Test 1: ECMP Incast
echo -e "\n=== Test 1: ECMP Incast ==="
python3 "$ROOT_DIR/experiments/incast_test.py" \
    --config "$ROOT_DIR/configs/experiment_config.json" \
    2>&1 | tee "$LOG_DIR/ecmp_incast_$TIMESTAMP.log"

# Test 2: HULA Incast
echo -e "\n=== Test 2: HULA Incast ==="
python3 "$ROOT_DIR/experiments/incast_test.py" \
    --config "$ROOT_DIR/configs/experiment_config.json" \
    2>&1 | tee "$LOG_DIR/hula_incast_$TIMESTAMP.log"

# Test 3: Microburst
echo -e "\n=== Test 3: Microburst ==="
python3 "$ROOT_DIR/experiments/microburst_test.py" \
    --config "$ROOT_DIR/configs/experiment_config.json" \
    2>&1 | tee "$LOG_DIR/microburst_$TIMESTAMP.log"

# Test 4: Link Failure
echo -e "\n=== Test 4: Link Failure ==="
python3 "$ROOT_DIR/experiments/link_failure_test.py" \
    --config "$ROOT_DIR/configs/experiment_config.json" \
    2>&1 | tee "$LOG_DIR/link_failure_$TIMESTAMP.log"

echo -e "\n=== All experiments complete! ==="
echo "Logs saved to:    $LOG_DIR"
echo "Results saved to: $RESULTS_DIR"

# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------
echo -e "\n=== Generating plots ==="
python3 "$ROOT_DIR/analysis/plot_results.py" --all

echo -e "\n=== Files currently in results/ ==="
ls -1 "$RESULTS_DIR" || echo "(results directory is empty)"

echo -e "\n✓ Done!"
