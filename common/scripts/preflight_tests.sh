#!/bin/bash
set -e

# Run preflight functional tests
python /app/common/preflight/run.py

# Start API server in the background and save its process ID to a file
python api/__main__.py & echo $! > /tmp/api_pid.txt

# Wait for the API server to start
sleep 10

# Change to the 'ui' directory and run Cypress tests
cd ui
cypress run
cypress_exit_code=$?

# Kill the API server process and exit with the Cypress exit code
kill $(cat /tmp/api_pid.txt)
exit $cypress_exit_code