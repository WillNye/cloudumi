# Easy Deploy

- Reference link: https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/quickcreate?templateURL=https%3A%2F%2Fs3.us-west-2.amazonaws.com%2Fbc-cf-template-890234264427-prod%2Fread_only_template.yml&param_ExternalID=baf62b81-52ea-4e75-8fb5-6428d586af3f&stackName=mattdaue-bridgecrew-read&param_ResourceNamePrefix=mattdaue-bc-read&param_CustomerName=mattdaue
- NOQ link (mattdaue): https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/quickcreate?templateURL=https%3A%2F%2Fs3.us-east-1.amazonaws.com%2Fcloudumi-cf-templates%2Fiam_stack_ecs.cf.yaml&param_ExternalID=baf62b81-52ea-4e75-8fb5-6428d586af3f&stackName=mattdaue-cloudumi-iam&param_ResourceNamePrefix=mattdaue-cloudumi-iam&param_CustomerName=mattdaue
- NOQ link (ccastrapel): https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/quickcreate?templateURL=https%3A%2F%2Fs3.us-east-1.amazonaws.com%2Fcloudumi-cf-templates%2Fiam_stack_ecs.cf.yaml&param_ExternalID=caf62b81-52ea-4e75-8fb5-6428d586af3f&stackName=ccastrapel-cloudumi-iam&param_ResourceNamePrefix=ccastrapel-cloudumi-iam&param_CustomerName=ccastrapel

## Central Role

- Execute `./deploy_central_role.sh` with AWS_PROFILE of your choice (for dev purposes only)