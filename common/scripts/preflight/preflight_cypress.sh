#!/bin/bash

# Show commands
set -x

# Activate virtualenv
source /app/env/bin/activate

temp_files_bucket=$(python -c 'from common.config import config; print(config.get("_global_.s3_buckets.temp_files"))')
[ "$temp_files_bucket" ] && [ "$temp_files_bucket" != "None" ] || { echo "Configuration not found for _global_.s3_buckets.temp_files"; exit 1; }
# Get the bucket region
bucket_region=$(/usr/local/bin/aws s3api get-bucket-location --bucket "$temp_files_bucket" --query "LocationConstraint" --output text)

# Check if the bucket region is empty (indicating the bucket is in the default region)
if [ -z "$bucket_region" ]; then
  bucket_region="us-east-1"  # Set the default region
fi

timestamp=$(date +%Y%m%d-%H%M%S)
bucket_path="${timestamp}-cypress"

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


# Install preflight deps
npm install cypress -g

pip install alembic
yarn --cwd ui
yarn --cwd ui add ts-node
export GEVENT_SUPPORT="True"
export TZ=UTC

# Change `development` to `True`. This is needed
# so the API server respects the X-Forwarded-For header
/usr/local/bin/aws s3 cp "${CONFIG_LOCATION}" /tmp/temp_config.yaml
sed -i 's/ development: false/ development: true/g' /tmp/temp_config.yaml
export CONFIG_LOCATION=/tmp/temp_config.yaml

# Start API server in the background, save its process ID to a file, and redirect its output to a log file
RUNTIME_PROFILE=API python api/__main__.py > /tmp/api_output.log 2>&1 & echo $! > /tmp/api_pid.txt

# Tail the API server log to the screen in the background and save its process ID to a file
tail -f /tmp/api_output.log 2>&1 | tee /tmp/api_output_screen.log & echo $! > /tmp/tail_pid.txt

# Wait for the API server to start
max_wait_time=600
wait_time=0
while ! grep -q "Server started" /tmp/api_output.log && [ $wait_time -lt $max_wait_time ]; do
  sleep 1
  wait_time=$((wait_time+1))
done

if [ $wait_time -ge $max_wait_time ]; then
  echo "Error: Server did not start within the specified time"
  exit 1
fi

# # Generate a random domain and add it to the /etc/hosts file
# random_digits=$(shuf -i 1000-9999 -n 1)
# domain="test-${random_digits}.example.com"
# email="cypress_ui_saas_functional_tests+${randomDigits}@noq.dev"
# echo "127.0.0.1 ${domain}" | sudo tee -a /etc/hosts
# export TEST_DOMAIN=${domain}
# export TEST_EMAIL=${email}

# Change to the 'ui' directory and run Cypress tests
cd ui
CYPRESS_TS_NODE_REGISTER=true cypress run 2>&1 | tee /tmp/cypress_output.log
cypress_exit_code=${PIPESTATUS[0]}


# Upload Cypress screenshots, videos, and logs to S3 and print the URLs
screenshots_tar="/tmp/cypress_screenshots.tar.gz"
tar czf "${screenshots_tar}" -C /app/ui/cypress/screenshots .
screenshots_presigned_url=$(generate_presigned_url "${screenshots_tar}")
echo "Screenshots Presigned URL: $screenshots_presigned_url"

video_presigned_urls=""
video_urls=""
for video in /app/ui/cypress/videos/*.mp4; do
  video_presigned_url=$(generate_presigned_url "${video}")
  video_urls="${video_urls}\n<${video_presigned_url}|${video}>"
  video_presigned_urls="${video_presigned_urls}${video_presigned_url}\n"
done

cypress_logs_presigned_url=$(generate_presigned_url /tmp/cypress_output.log)
api_logs_presigned_url=$(generate_presigned_url /tmp/api_output.log)

echo "Videos Presigned URLs:"
echo -e "${video_presigned_urls}"
echo "Cypress Logs Presigned URL: $cypress_logs_presigned_url"
echo "API Server Logs Presigned URL: $api_logs_presigned_url"

# Kill the tail process
kill $(cat /tmp/tail_pid.txt) || true

# Kill the API server process and exit with the Cypress exit code
# sudo sed -i "/${domain}/d" /etc/hosts || true

# Kill the API server process and exit with the Cypress exit code
kill $(cat /tmp/api_pid.txt) || true

if [ $cypress_exit_code -ne 0 ]; then
  echo "Cypress UI tests failed with exit code: $cypress_exit_code"

  send_to_slack '{
    "text": "Cypress UI tests failed with exit code: '"$cypress_exit_code"'. Check the logs for more information.",
    "blocks": [
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Cypress UI tests failed with exit code: '"$cypress_exit_code"'*\nCheck the logs for more information."
        }
      },
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Cypress videos Presigned URLs:*\n'"$video_urls"'"
        }
      },
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Cypress screenshots Presigned URL:*\n<'"$screenshots_presigned_url"'|link>"
        }
      },
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Cypress logs Presigned URL:*\n<'"$cypress_logs_presigned_url"'|link>"
        }
      },
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*API Server Logs Presigned URL:*\n<'"$api_logs_presigned_url"'|link>"
        }
      }
    ]
  }'
  exit $cypress_exit_code
else
  echo "Cypress UI tests finished successfully."

  send_to_slack '{
    "text": "Cypress UI tests finished successfully. Check the logs for more information.",
    "blocks": [
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Cypress UI tests finished successfully*\nCheck the logs for more information."
        }
      },
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Cypress videos Presigned URLs:*\n'"$video_urls"'"
        }
      },
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Cypress screenshots Presigned URL:*\n<'"$screenshots_presigned_url"'|link>"
        }
      },
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Cypress logs Presigned URL:*\n<'"$cypress_logs_presigned_url"'|link>"
        }
      },
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*API Server Logs Presigned URL:*\n<'"$api_logs_presigned_url"'|link>"
        }
      }
    ]
  }'
  exit 0
fi


# Exit with the Cypress exit code
exit $cypress_exit_code
