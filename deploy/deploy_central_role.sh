#!/bin/bash
aws cloudformation create-stack --stack-name cloudumi-central-acct-test --template-body file://`pwd`/cloudumi_central_role.yaml --parameters ParameterKey=ExternalIDParameter,ParameterValue=1234567 --capabilities CAPABILITY_NAMED_IAM
