#!/bin/bash
pip install --target . -r requirements.txt
zip -r deployment.zip .
aws lambda delete-function --function-name handleNoqRegistrationResponseToCF
aws lambda create-function --function-name handleNoqRegistrationResponseToCF \
--zip-file fileb://deployment.zip --handler handler.emit_s3_response --runtime python3.9 \
--role arn:aws:iam::259868150464:role/lambda-ex
aws lambda create-event-source-mapping --function-name handleNoqRegistrationResponseToCF \
--batch-size 10 --event-source-arn arn:aws:sqs:us-east-1:259868150464:noq_registration_response_queue
echo "ERRORS CAN BE SOMEWHAT IGNORED FOR NOW"