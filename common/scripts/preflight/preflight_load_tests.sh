#!/bin/bash

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

# Check the locust exit code and print the output log in case of failure
if [ $locust_exit_code -ne 0 ]; then
  echo "Locust load tests failed with exit code: $locust_exit_code"
  echo "Printing locust output:"
  cat /tmp/locust_output.log
  exit $locust_exit_code
else
  echo "Locust load tests finished successfully"
  exit 0
fi
