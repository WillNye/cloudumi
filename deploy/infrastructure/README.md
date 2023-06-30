To get started with Terraform for this project, follow these steps:

1. Install `tfenv` to manage Terraform versions easily:

   For MacOS:

   ```
   brew install tfenv
   ```

   For Linux:

   ```
   git clone https://github.com/tfutils/tfenv.git ~/.tfenv
   ln -s ~/.tfenv/bin/* /usr/local/bin
   ```

2. Set the desired Terraform version (use the latest stable version):

   ```
   tfenv install latest
   tfenv use latest
   ```

3. Make sure you have the latest `secret.tfvars` file. You can find it in the AWS Secrets Manager in the respective account and region. The structure of the file should look like this (make sure to ask a coworker to double-check, as missing secrets could cause issues in staging or production environments):

   ```
   # File must have a new line at the bottom
   redis_secrets                      = "hidden"
   noq_db_username                    = "hidden"
   noq_db_password                    = "hidden"
   aws_secrets_manager_cluster_string = <<-EOT
   _global_:
     secrets:
       slack:
         app_id: hidden
         app_token: hidden
         bot_token: hidden
         client_id: "hidden"
         client_secret: hidden
         signing_secret: hidden
       sendgrid:
         from_address: notifications@noq.dev
         username: hidden
         password: hidden
       redis:
         password: hidden
       postgresql:
         username: hidden
         password: hidden
   EOT
   ```

4. The Makefile will set the `BASE_DIR` for you, so no need to set it manually.

5. Use the following commands to refresh, plan, and apply changes in staging and production environments:

   - Staging:

     ```
     make tf-staging-refresh
     make tf-staging-plan
     make tf-staging-apply
     ```

   - Production:
     ```
     make tf-prod-refresh
     make tf-prod-plan
     make tf-prod-apply
     ```

You don't need to run `terraform plan` or `terraform apply` manually, as the Makefile provides commands for them. Follow these steps, and you should be good to go.
