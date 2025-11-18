#!/bin/bash

echo "=== Cleaning up P4 project ==="

# Stop Mininet
sudo mn -c

# Kill any running switches
sudo killall simple_switch simple_switch_grpc

# Clean build artifacts
rm -rf ../build/*.json ../build/*.p4info.txt ../build/*.p4i

# Clean logs (keep directory)
rm -f ../logs/*.log ../logs/*.pcap

# Clean results (optional - comment out if you want to keep)
# rm -f ../results/*.json

echo "✓ Cleanup complete"
