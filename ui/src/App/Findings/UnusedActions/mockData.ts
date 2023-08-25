export const dataTable = Array.from({ length: 10 }).map(() => ({
  identity_name: 'MonitoringServiceRole',
  identity_type: 'IAM Role',
  accounts: [
    {
      name: 'Prod',
      account: 833386978371
    },
    {
      name: 'Development',
      account: 944491932382
    }
  ],
  description: '5 Unused actions',
  status: 'Open',
  last_activity: new Date().toDateString()
}));
