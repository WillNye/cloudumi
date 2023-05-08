#!/bin/bash

# Activate virtualenv
source /app/env/bin/activate

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

# Install preflight deps
npm install cypress -g

pip install alembic
yarn --cwd ui
yarn --cwd ui add ts-node
export GEVENT_SUPPORT="True"

# Change `development` to `True`. This is needed
# so the API server respects the X-Forwarded-For header
aws s3 cp "${CONFIG_LOCATION}" /tmp/temp_config.yaml
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

# Generate a random domain and add it to the /etc/hosts file
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


# Upload Cypress screenshots, videos, and logs to transfer.sh and print the URLs
screenshots_tar="/tmp/cypress_screenshots.tar.gz"
tar czf "${screenshots_tar}" -C /app/ui/cypress/screenshots .
screenshots_url=$(upload_to_transfer_sh "${screenshots_tar}")
echo "Screenshots URL: $screenshots_url"

video_urls=""
for video in /app/ui/cypress/videos/*.mp4; do
  video_url=$(upload_to_transfer_sh "${video}")
  video_urls="${video_urls}${video_url}\n"
done

cypress_logs_url=$(upload_to_transfer_sh /tmp/cypress_output.log)

api_logs_url=$(upload_to_transfer_sh /tmp/api_output.log)

echo "Videos URLs:"
echo -e "${video_urls}"
echo "Cypress Logs URL: $cypress_logs_url"
echo "API Server Logs URL: $api_logs_url"

# Kill the tail process
kill $(cat /tmp/tail_pid.txt) || true

# Kill the API server process and exit with the Cypress exit code
# sudo sed -i "/${domain}/d" /etc/hosts || true

# Kill the API server process and exit with the Cypress exit code
kill $(cat /tmp/api_pid.txt) || true

# Check the cypress exit code and send the summary to the Slack webhook
if [ $cypress_exit_code -ne 0 ]; then
  echo "Cypress UI tests failed with exit code: $cypress_exit_code"
  send_to_slack "Cypress UI tests failed with exit code: $cypress_exit_code. Check the logs for more information.\nCypress videos URLs:\n${video_urls}\nCypress screenshots URL: ${screenshots_url}\nCypress logs URL: ${cypress_logs_url}\nAPI Server Logs URL: ${api_logs_url}"
  exit $cypress_exit_code
else
  echo "Cypress UI tests finished successfully."
  send_to_slack "Cypress UI tests finished successfully. Check the logs for more information.\nCypress videos URLs:\n${video_urls}\nCypress screenshots URL: ${screenshots_url}\nCypress logs URL: ${cypress_logs_url}\nAPI Server Logs URL: ${api_logs_url}"
  exit 0
fi

# Exit with the Cypress exit code
exit $cypress_exit_code
