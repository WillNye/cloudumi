**Central Account Role Permissions**

Noq will always assume in to your central account role in order to access your environment. This is Noq's entrypoint in to your environment. As a security precaution, Noq assigns a random ExternalID to your tenant on Noq. We will always pass this ExternalId when assuming a role. If the ExternalId does not match, the assume role connection will not be permitted.

Noq also has the capability to broker credentials to authorized users or groups for all other roles within your environment. To allow this, please enable credential brokering in the Settings page, and specify tags that Noq can use to identify the authorized users and groups allowed to access each role.

The Central Role requires the following permissions:

| Permission     | Resource | Purpose                                                                                                                                                                                                                                                     |
| -------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| sts:AssumeRole | \*\*     | Assume all Noq spoke roles across the customer's accounts. Assume all roles for the purpose of credential brokering (Note: This only works if the target roles allow the Central Role to call sts:AssumeRole and sts:TagSession within their Trust Policy.) |
| sts:TagSession | \*\*     | Allow Noq to pass session tags when performing a role assumption.                                                                                                                                                                                           |

**Spoke Role Account Permissions**

Noq's spoke roles are assumed by the Noq central role to cache information about your accounts and cloud resources, and to update identity and resource policies. One spoke role should exist on each of your accounts, including the account that your central role resides on.

Noq performs the following steps to cache IAM resources across your account:

1. Assume Central Role with unique ExternalID

2. Assume Spoke Role on the target account

3. Use Spoke Role credentials to call IAM APIs to determine resources

| Permission                                    | Resource | Purpose                                                                      |
| --------------------------------------------- | -------- | ---------------------------------------------------------------------------- |
| config:BatchGet\*                             | \*\*     | Retrieve AWS Config details for your resources ; Will allow policy rollback  |
| config:List\*                                 | \*\*     | Retrieve information about AWS resources to list in a single source of truth |
| config:Select\*                               | \*\*     | Query AWS Config                                                             |
| ec2:describeregions                           | \*\*     | Retrieve active regions for your AWS environment                             |
| iam:AttachRolePolicy                          | \*\*     | Attach managed policies to IAM roles                                         |
| iam:AttachUserPolicy                          | \*\*     | Attach managed policies to IAM users                                         |
| iam:CreateInstanceProfile                     | \*\*     | Create an instance profile (We do this when creating or cloning roles)       |
| iam:CreateRole                                | \*\*     | Create or clone an IAM role                                                  |
| iam:DeleteAccessKey                           | \*\*     | Delete an IAM access key during IAM user deletion                            |
| iam:DeleteInstanceProfile                     | \*\*     | Delete instance profiles during role deletion                                |
| iam:DeleteRole                                | \*\*     | Allows Noq to delete roles                                                   |
| iam:DeletePolicy                              | \*\*     | Delete managed policies                                                      |
| iam:DeletePolicyVersion                       | \*\*     | Delete a managed policy version, used when updating managed policies         |
| iam:DeleteRolePermissionsBoundary             | \*\*     | Remove a permissions boundary from a role                                    |
| iam:DeleteRolePolicy                          | \*\*     | Remove an inline policy from a role                                          |
| iam:DeleteUser                                | \*\*     | Allows Noq to delete users                                                   |
| iam:DeleteUserPermissionsBoundary             | \*\*     | Allows Noq to remove a user's permission boundary                            |
| iam:DeleteUserPolicy                          | \*\*     | Allow Noq to delete User inline policies                                     |
| iam:DeleteVirtualMFADevice                    | \*\*     | Used by Noq when deleting IAM users                                          |
| iam:DetachRolePolicy                          | \*\*     | Allow Noq to remove managed policies from IAM roles                          |
| iam:DetachUserPolicy                          | \*\*     | Allow Noq to remove managed policies from IAM users                          |
| iam:GenerateCredentialReport                  | \*\*     | Generate credential usage report                                             |
| iam:GenerateOrganizationsAccessReport         | \*\*     | Generates a report for service last accessed data for Organizations.         |
| iam:GenerateServiceLastAccessedDetails        | \*\*     | Use Access Advisor to determine unused services for IAM roles and users      |
| iam:GetAccessKeyLastUsed                      | \*\*     | Determine when an IAM access key was last used                               |
| iam:GetAccountAuthorizationDetails            | \*\*     | Retrieve context about all IAM resources on the account.                     |
| iam:GetAccountSummary                         | \*\*     | Retrieves account status and quota details                                   |
| iam:GetCredentialReport                       | \*\*     | Determine status of IAM credentials on an account                            |
| iam:GetGroup                                  | \*\*     | Get an IAM group                                                             |
| iam:GetGroupPolicy                            | \*\*     | Get the policy for an IAM group                                              |
| iam:GetInstanceProfile                        | \*\*     | Get details about an instance profile                                        |
| iam:GetPolicy                                 | \*\*     | Retrieve information about a manged policy                                   |
| iam:GetPolicyVersion                          | \*\*     | Retrieve a specific version of an IAM managed policy                         |
| iam:GetRole                                   | \*\*     | Get a role (Used for policy editing and self-service)                        |
| iam:GetRolePolicy                             | \*\*     | Get a role's inline policy (Used for policy editing and self-service)        |
| iam:GetServiceLastAccessedDetails             | \*\*     | Used for removing unused service permissions                                 |
| iam:GetServiceLastAccessedDetailsWithEntities | \*\*     | Used for removing unused service permissions                                 |
| iam:GetUser                                   | \*\*     | Retrieve an IAM user for policy editing and self-service                     |
| iam:GetUserPolicy                             | \*\*     | Retrieve an IAM user inline policy for policy editing and self-service       |
| iam:ListAccessKeys                            | \*\*     | List IAM user access keys                                                    |
| iam:ListAccountAliases                        | \*\*     | List account aliases for determining account name                            |
| iam:ListAttachedRolePolicies                  | \*\*     | Used for policy editing / self-service                                       |
| iam:ListAttachedUserPolicies                  | \*\*     | Used for policy editing / self-service                                       |
| iam:ListEntitiesForPolicy                     | \*\*     | Used for policy editing / self-service                                       |
| iam:ListGroupPolicies                         | \*\*     | Used for policy editing / self-service                                       |
| iam:ListGroups                                | \*\*     | Used for policy editing / self-service                                       |
| iam:ListGroupsForUser                         | \*\*     | Used for policy editing / self-service                                       |
| iam:ListInstanceProfileTags                   | \*\*     | Used for policy editing / self-service                                       |
| iam:ListInstanceProfiles                      | \*\*     | Used for policy editing / self-service                                       |
| iam:ListInstanceProfilesForRole               | \*\*     | Used for policy editing / self-service                                       |
| iam:ListPolicies                              | \*\*     | Used to cache managed policy names                                           |
| iam:ListPolicyTags                            | \*\*     | Used for policy editing / self-service                                       |
| iam:ListPolicyVersions                        | \*\*     | Used for policy editing / self-service                                       |
| iam:ListRolePolicies                          | \*\*     | Used for policy editing / self-service                                       |
| iam:ListRoleTags                              | \*\*     | Used for policy editing / self-service                                       |
| iam:ListRoles                                 | \*\*     | Used for policy editing / self-service                                       |
| iam:ListUserPolicies                          | \*\*     | Used for policy editing / self-service                                       |
| iam:ListUserTags                              | \*\*     | Used for policy editing / self-service                                       |
| iam:ListUsers                                 | \*\*     | Used for policy editing / self-service                                       |
| iam:PutRolePermissionsBoundary                | \*\*     | Used for policy editing / self-service                                       |
| iam:PutRolePolicy                             | \*\*     | Used for policy editing / self-service                                       |
| iam:PutUserPermissionsBoundary                | \*\*     | Used for policy editing / self-service                                       |
| iam:PutUserPolicy                             | \*\*     | Used for policy editing / self-service                                       |
| iam:RemoveRoleFromInstanceProfile             | \*\*     | Used when deleting roles                                                     |
| iam:RemoveUserFromGroup                       | \*\*     | Used when deleting users                                                     |
| iam:SetDefaultPolicyVersion                   | \*\*     | Used when updating managed policies                                          |
| iam:SimulateCustomPolicy                      | \*\*     | Used when determining if an action is allowed                                |
| iam:SimulatePrincipalPolicy                   | \*\*     | Used when determining if an action is allowed                                |
| iam:TagInstanceProfile                        | \*\*     | Used when creating a role                                                    |
| iam:TagPolicy                                 | \*\*     | Used for policy editing / self-service                                       |
| iam:TagRole                                   | \*\*     | Used for policy editing / self-service                                       |
| iam:TagUser                                   | \*\*     | Used for policy editing / self-service                                       |
| iam:UntagInstanceProfile                      | \*\*     | Used when deleting a role                                                    |
| iam:UntagPolicy                               | \*\*     | Used for policy editing / self-service                                       |
| iam:UntagRole                                 | \*\*     | Used for policy editing / self-service                                       |
| iam:UntagUser                                 | \*\*     | Used for policy editing / self-service                                       |
| iam:UpdateAssumeRolePolicy                    | \*\*     | Used for policy editing / self-service                                       |
| iam:UpdateRole                                | \*\*     | Used for policy editing / self-service                                       |
| iam:UpdateRoleDescription                     | \*\*     | Used for policy editing / self-service                                       |
| iam:UpdateUser                                | \*\*     | Used for policy editing / self-service                                       |
| s3:GetBucketPolicy                            | \*\*     | Retrieve information about your S3 buckets ; Enable modifying buckets        |
| s3:GetBucketTagging                           | \*\*     | Used for policy editing / self-service                                       |
| s3:ListAllMyBuckets                           | \*\*     | Cache all bucket ARNs for typeahead and policy editing                       |
| s3:ListBucket                                 | \*\*     | Used for policy editing / self-service                                       |
| s3:PutBucketPolicy                            | \*\*     | Used for policy editing / self-service                                       |
| s3:PutBucketTagging                           | \*\*     | Used for policy editing / self-service                                       |
| sns:GetTopicAttributes                        | \*\*     | Retrieve information about your SNS topics ; Enable modifying topics         |
| sns:ListTagsForResource                       | \*\*     | Used for policy editing / self-service                                       |
| sns:ListTopics                                | \*\*     | Policy editing, and global view of all SNs topics                            |
| sns:SetTopicAttributes                        | \*\*     | Used for policy editing / self-service                                       |
| sns:TagResource                               | \*\*     | Used for policy editing / self-service                                       |
| sns:UnTagResource                             | \*\*     | Used for policy editing / self-service                                       |
| sqs:GetQueueAttributes                        | \*\*     | Retrieve information about your SQS queues ; Enable modifying queues         |
| sqs:GetQueueUrl                               | \*\*     | Used in SNS policy editor                                                    |
| sqs:ListQueues                                | \*\*     | Used to provide global view of all SQS queues                                |
| sqs:ListQueueTags                             | \*\*     | Used for policy editing / self-service                                       |
| sqs:SetQueueAttributes                        | \*\*     | Used for policy editing / self-service                                       |
| sqs:TagQueue                                  | \*\*     | Used for policy editing / self-service                                       |
| sqs:UntagQueue                                | \*\*     |                                                                              |
