export const contents = [
  {
    handler: 'aws-iam-roles',
    Content: () => <>aws-iam-roles</>,
  },
  {
    handler: 'hub-account',
    Content: () => <>hub-account</>,
  },
  {
    handler: 'spoke-accounts',
    Content: () => <>spoke-accounts</>,
  },
  {
    handler: 'aws-organization',
    Content: () => <>aws-organization</>,
  },
  {
    handler: 'role-access-authorization',
    Content: () => <>role-access-authorization</>,
  },
]

export const helpContent = (handler) => {
  return contents.filter((i) => i.handler === handler)?.[0]
}
