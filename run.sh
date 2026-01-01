#!/bin/bash

# Navigate to the project root
cd "$(dirname "$0")"

# Install dependencies if not already installed (checking for a random package to be quicker, or just run pip)
echo "Installing dependencies..."
pip install -r app/requirements.txt

# Run the application
echo "Starting server..."
# Run from the parent directory so that 'app' module is found
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
