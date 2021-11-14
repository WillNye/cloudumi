#!/bin/bash
pip install --target . -r requirements.txt
zip -r deployment.zip .
aws lambda create-function --function-name handleNoqRegistrationResponseToCF \
--zip-file fileb://deployment.zip --handler handler.emit_s3_response --runtime python3.9 \
--role arn:aws:iam::259868150464:role/lambda-ex