export const dataTable = Array.from({ length: 2 }).map(() => ({
  creation_date: new Date().toDateString(),
  // accounts: [
  //   {
  //     name: 'Prod',
  //     account: 833386978371
  //   },
  //   {
  //     name: 'Development',
  //     account: 944491932382
  //   }
  // ],
  last_activity: new Date().toDateString(),
  unused_services: 1,
  unused_actions: 29
}));

export const oldTemplate = `template_schema_url: https://docs.iambic.org/reference/schemas/aws_iam_group_template
template_type: NOQ::AWS::IAM::Group
included_accounts:
  - development
identifier: ctaccess
properties:
  group_name: ctaccess
  managed_policies:
    - policy_arn: arn:aws:iam::aws:policy/AWSCloudTrail_ReadOnlyAccess
`;

export const newTemplate = `template_schema_url: https://docs.iambic.org/reference/schemas/aws_iam_group_template
template_type: NOQ::AWS::IAM::Group
included_accounts:
  - development
identifier: ctaccess
properties:
  group_name: ctaccess
  managed_policies:
  - policy_arn: arn:aws:iam::aws:policy/AWSCloudTrail_ReadOnlyAccess
  included_accounts:
  - development
identifier: ctaccess
properties:
  group_name: ctaccess
  managed_policies:
  - policy_arn: arn:aws:iam::aws:policy/AWSCloudTrail_ReadOnlyAccess
properties:
  group_name: ctaccess
  managed_policies:
    - policy_arn: arn:aws:iam::aws:policy/AWSCloudTrail_ReadOnlyAccess
`;
