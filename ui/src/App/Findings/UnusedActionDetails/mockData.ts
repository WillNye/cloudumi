export const dataTable = Array.from({ length: 2 }).map(() => ({
  creation_date: new Date().toDateString(),
  last_activity: new Date().toDateString(),
  unused_services: 1,
  unused_actions: 29
}));

export const unusedActionsList = [
  {
    resource: 'Amazon Connect',
    actions: [
      {
        resource_identity: 'GetFederationToken',
        severity: 'critical',
        last_accessed: 'Never used'
      }
    ]
  },
  {
    resource: 'Amazon S3',
    actions: [
      {
        resource_identity: 'BypassGovernanceRetention',
        severity: 'critical',
        last_accessed: '200 days ago'
      },
      {
        resource_identity: 'BypassGovernanceRetention',
        severity: 'critical',
        last_accessed: '200 days ago'
      }
    ]
  },
  {
    resource: 'EC2',
    actions: [
      {
        resource_identity: 'AcceptVpcEndpointConnection',
        severity: 'critical',
        last_accessed: '90 days ago'
      },
      {
        resource_identity: 'CancelExportTask',
        severity: 'low',
        last_accessed: '105 days ago'
      },
      {
        resource_identity: 'CreateClicentVpnRoute',
        severity: 'low',
        last_accessed: '355 days ago'
      },
      {
        resource_identity: 'CreateDefaultSubnet',
        severity: 'low',
        last_accessed: '355 days ago'
      },
      {
        resource_identity: 'CreateInstance ConnectEnd',
        severity: 'low',
        last_accessed: '91 days ago'
      },
      {
        resource_identity: 'CreateNetworkInterfacePermission',
        severity: 'critical',
        last_accessed: '200 days ago'
      }
    ]
  }
];

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
