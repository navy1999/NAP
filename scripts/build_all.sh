#!/bin/bash
set -e

echo "Building P4 programs..."

mkdir -p build

# Compile ECMP
p4c --target bmv2 --arch v1model \
    --p4runtime-files build/ecmp.p4info.txt \
    -o build/ecmp.json \
    p4src/ecmp.p4

echo "✓ ECMP compiled"

# Compile HULA
p4c --target bmv2 --arch v1model \
    --p4runtime-files build/hula.p4info.txt \
    -o build/hula.json \
    p4src/hula.p4

echo "✓ HULA compiled"

echo "All P4 programs built successfully!"
