#!/bin/bash

# Function to send messages to Slack webhook
send_to_slack() {
  webhook_url="A_SECRET"
  message=$1
  curl -X POST -H 'Content-type: application/json' --data "{'text': '${message}'}" ${webhook_url}
}

# Function to upload a file to transfer.sh and return the download URL
upload_to_transfer_sh() {
  filepath=$1
  filename=$(basename "${filepath}")
  transfer_url=$(curl --progress-bar --upload-file "${filepath}" "https://transfer.sh/${filename}")
  echo "${transfer_url}"
}

# Start API server in the background, save its process ID to a file, and redirect its output to a log file
RUNTIME_PROFILE=API python api/__main__.py > /tmp/api_output.log 2>&1 & echo $! > /tmp/api_pid.txt
# Tail the API server log to the screen in the background and save its process ID to a file
tail -f /tmp/api_output.log 2>&1 & echo $! > /tmp/tail_pid.txt
# Wait for the API server to start
max_wait_time=600
wait_time=0
while ! grep -q "Server started" /tmp/api_output.log && [ $wait_time -lt $max_wait_time ]; do
  sleep 1
  wait_time=$((wait_time+1))
done

if [ $wait_time -ge $max_wait_time ]; then
  echo "Error: Server did not start within ${max_wait_time} seconds"
  exit 1
fi
# Run the load tests and redirect output to a log file
python -m locust -f load_tests/locustfile.py --headless -u 10 -r 5 -t 60 > /tmp/locust_output.log 2>&1
locust_exit_code=$?
# Kill the tail process
kill $(cat /tmp/tail_pid.txt) || true

# Kill the API server process
kill $(cat /tmp/api_pid.txt) || true

# Print locust output and upload it to transfer.sh
echo "Printing locust output:"
cat /tmp/locust_output.log
transfer_url=$(upload_to_transfer_sh "/tmp/locust_output.log")
echo "Uploaded locust output to transfer.sh: ${transfer_url}"

# Check the locust exit code and send the summary to the Slack webhook
if [ $locust_exit_code -ne 0 ]; then
  echo "Locust load tests failed with exit code: $locust_exit_code"
  send_to_slack "Locust load tests failed with exit code: $locust_exit_code. Check the logs for more information. Locust output: ${transfer_url}"
  exit $locust_exit_code
else
  echo "Locust load tests finished successfully"
  send_to_slack "Locust load tests finished successfully. Locust output: ${transfer_url}"
  exit 0
fi
