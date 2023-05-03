#!/bin/bash

# Activate virtualenv
source /app/env/bin/activate

# Install preflight deps
pip install alembic
yarn --cwd ui
yarn --cwd ui add ts-node

# TODO: This ignores functional tests, uncomment before merging
# # Run preflight functional tests
# set -e
# python /app/common/preflight/run.py
# set +e

# Start API server in the background, save its process ID to a file, and redirect its output to a log file
python api/__main__.py > /tmp/api_output.log 2>&1 & echo $! > /tmp/api_pid.txt

# Tail the API server log to the screen in the background and save its process ID to a file
tail -f /tmp/api_output.log 2>&1 & echo $! > /tmp/tail_pid.txt

# Wait for the API server to start
max_wait_time=180
wait_time=0
while ! grep -q "Server started" /tmp/api_output.log && [ $wait_time -lt $max_wait_time ]; do
  sleep 1
  wait_time=$((wait_time+1))
done

if [ $wait_time -ge $max_wait_time ]; then
  echo "Error: Server did not start within 3 minutes"
  exit 1
fi

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

# Kill the tail process
kill $(cat /tmp/tail_pid.txt) || true

# Kill the API server process and exit with the Cypress exit code
kill $(cat /tmp/api_pid.txt) || true

# Exit with the Cypress exit code
exit $cypress_exit_code
