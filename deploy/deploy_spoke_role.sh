#!/bin/bash
#aws cloudformation create-stack --stack-name cloudumi-spoke-acct-test --template-body file://`pwd`/cloudumi_spoke_role.yaml --parameters ParameterKey=ExternalIDParameter,ParameterValue=1234567 --parameters ParameterKey=CloudUmiCentralAcctArn,ParameterValue=arn:aws:iam::259868150464:role/cloudumi-central-role-c2c7f160 --capabilities CAPABILITY_NAMED_IAM
aws cloudformation create-stack --stack-name cloudumi-spoke-acct-test --template-body file://`pwd`/cloudumi_spoke_role.yaml --parameters file://parameters_spoke.json --capabilities CAPABILITY_NAMED_IAM
