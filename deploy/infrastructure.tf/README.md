# NOQ Infrastructure
Each NOQ infrastructure is setup in it's own tenant and account id. When needed, a new deployment configuration tfvars is added to the `live` directory under the new tenant id. Use this only to setup a new account backend infrastructure and to update the infrastructure when changes are needed.

## Quick Start
Ensure the AWS_PROFILE is set to the correct account id
* `EXPORT AWS_PROFILE=noq_dev` (for instance)
* For the first time, initialize the environment: `terraform init`
* Plan: `terraform plan --var-file=live/demo.noq.dev/demo.noq.dev.tfvars`
* Apply: `terraform apply --var-file=live/demo.noq.dev/demo.noq.dev.tfvars`
* Destroy: `terraform destroy --var-file=live/demo.noq.dev/demo.noq.dev.tfvars`

## Structure
* `live`: has configuration tfvars for each tenant that is instantiated
  * Each tenant should be stored in it's own directory using the form: `<tenant name>.noq.dev`, which should echo the tenant access URI
  * Updates can be achieved in the same way
  * Tenants can be destroyed as well; tenant configuration should be retained for historical records
* `modules`: has all infrastucture as code modules
  * `services`: has services to be configured for deployment
    * `dynamo`: the table configurations
    * `elasticache`: the redis table
    * `s3`: the bucket to be used for configuration
