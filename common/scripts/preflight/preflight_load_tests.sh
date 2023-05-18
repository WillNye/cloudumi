#!/bin/bash

# Show commands
set -x

# Activate virtualenv
source /app/env/bin/activate

temp_files_bucket=$(python -c 'from common.config import config; print(config.get("_global_.s3_buckets.temp_files"))')
[ "$temp_files_bucket" ] && [ "$temp_files_bucket" != "None" ] || { echo "Configuration not found for _global_.s3_buckets.temp_files"; exit 1; }
timestamp=$(date +%Y%m%d-%H%M%S)
bucket_path="${timestamp}-load_tests"
# Get the bucket region
bucket_region=$(/usr/local/bin/aws s3api get-bucket-location --bucket "$temp_files_bucket" --query "LocationConstraint" --output text)

# Check if the bucket region is empty (indicating the bucket is in the default region)
if [ -z "$bucket_region" ]; then
  bucket_region="us-east-1"  # Set the default region
fi

# Function to send messages to Slack webhook
send_to_slack() {
  webhook_url="A_SECRET"
  message=$1
  payload_file="payload.json"

  # Create a payload file
  echo "${message}" > "${payload_file}"

  # Send the payload using curl
  curl -X POST -H 'Content-type: application/json' --data "@${payload_file}" ${webhook_url}

  # Remove the payload file
  rm "${payload_file}"
}

# Function to generate a presigned URL for a file in S3
generate_presigned_url() {
  filepath=$1
  filename=$(basename "${filepath}")
  /usr/local/bin/aws s3 cp "${filepath}" "s3://${temp_files_bucket}/${bucket_path}/${filename}" > /dev/null
  /usr/local/bin/aws s3 presign --expires-in 600000 --region ${bucket_region} "s3://${temp_files_bucket}/${bucket_path}/${filename}"
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

# Print locust output and upload it to s3
echo "Printing locust output:"
cat /tmp/locust_output.log
s3_url=$(generate_presigned_url /tmp/locust_output.log)
echo "Uploaded locust output to s3: ${s3_url}"

# Check the locust exit code and send the summary to the Slack webhook
# Check the locust exit code and send the summary to the Slack webhook
if [ $locust_exit_code -ne 0 ]; then
  echo "Locust load tests failed with exit code: $locust_exit_code"

  send_to_slack '{
    "text": "Locust load tests failed with exit code: '"$locust_exit_code"'",
    "blocks": [
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Locust load tests failed with exit code: '"$locust_exit_code"'*\nCheck the logs for more information. Locust output: <'"$s3_url"'|link>"
        }
      }
    ]
  }'
  exit $locust_exit_code
else
  echo "Locust load tests finished successfully"

  send_to_slack '{
    "text": "Locust load tests finished successfully",
    "blocks": [
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Locust load tests finished successfully*\nLocust output: <'"$s3_url"'|link>"
        }
      }
    ]
  }'
  exit 0
fi

