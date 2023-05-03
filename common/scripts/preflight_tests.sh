#!/bin/bash

# Activate virtualenv
source /app/env/bin/activate

# Install preflight deps
pip install alembic
yarn --cwd ui
yarn --cwd ui add ts-node

# Run preflight functional tests
set -e
python /app/common/preflight/run.py
set +e

# Start API server in the background, save its process ID to a file, and redirect its output to a log file
python api/__main__.py > /tmp/api_output.log 2>&1 & echo $! > /tmp/api_pid.txt

# Wait for the API server to start
sleep 20

# Change to the 'ui' directory and run Cypress tests
cd ui
CYPRESS_TS_NODE_REGISTER=true cypress run || true
cypress_exit_code=$?

# Upload Cypress screenshots and videos to transfer.sh and print the URLs
echo "Uploading screenshots and videos to transfer.sh:"
screenshots_url=$(tar czf - cypress/screenshots/ | curl --progress-bar --upload-file - "https://transfer.sh/cypress-screenshots.tar.gz")
videos_url=$(tar czf - cypress/videos/ | curl --progress-bar --upload-file - "https://transfer.sh/cypress-videos.tar.gz")

echo "Screenshots URL: $screenshots_url"
echo "Videos URL: $videos_url"


# Print the API server stdout and stderr to the screen
echo "API server output:"
cat /tmp/api_output.log

# Kill the API server process and exit with the Cypress exit code
kill $(cat /tmp/api_pid.txt) || true

# Exit with the Cypress exit code
exit $cypress_exit_code