**Onboarding Instructions**

**Connect your AWS Central/Hub Account**

Noq uses a Hub and Spoke approach to connect to your AWS environment in order to cache cloud resources, make policy changes, and provide credential brokering features. Your hub role, or "central role", is Noq's entrypoint in to your environment. Noq assumes this role with an external ID that is unique to your environment. Each AWS account with Noq enabled should also have a spoke role that the central role can assume.

To onboard on to Noq, please create or choose an AWS account to serve as the account where Noq's Central Role is deployed. This can be any account in your environment. Then follow the steps below:

1. Log in to the AWS Console of the account where you would like to deploy Noq's Central Role

2. Visit **Advanced** -> **Settings**

3. Click **Connect Hub Role**

4. Click **Execute CloudFormation**

5. Run the CloudFormation Stack on the account. This will create a Hub Role and a Spoke Role on the account, then notify Noq when it has completed.

6. Wait a few minutes. Noq will verify the connection, add the Hub and Spoke roles to your account, and begin to cache resources on the account

After about 10 minutes, you should see cloud resources in your account. This is a great time to try out the self-service features.

TBD:

Screencast
Walk the user through Noq Self-Service after setting up their 1st account
Walk user through AWS Console Login experience, shortcuts, and 1-click-resource access
Walk user through Weep credential flows
Connect your AWS Spoke Account
Very similar process to the Hub Account
Walk the user through a cross-account permission request, and show cross-account policy generation
Enable AWS credential brokering in Noq
This will be a checkbox in our configuration
Add users, or connect your federated identity provider (most companies want this)
User can configure OAuth2 and SAML-compatible identity providers, such as Okta, Google, Auth0, Azure AD, etc.
Tag your roles with the users / groups that should have access to role credentials via Noq
Users can use the Self-Service wizard to update role tags
I’m going to use mkdocs, self-hosted. They are static files. We can wrap it behind CloudUmi auth from our Monorepo.
