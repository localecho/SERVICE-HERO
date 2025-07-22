#!/bin/bash
# Service Hero Test Runner

echo "SERVICE-HERO Test Suite"
echo "========================"

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo "Installing pytest..."
    pip install pytest pytest-asyncio
fi

# Run unit tests
echo "Running unit tests..."
python -m pytest test_service_hero.py -v

# Run integration tests  
echo "Running integration tests..."
python -m pytest test_integration.py -v

echo "Test suite completed!"