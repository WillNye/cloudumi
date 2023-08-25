export const unusedMetricsData = [
  {
    labelTitle: '38%',
    labelDescription: 'Are Unused Cloud Identities',
    title: 'Cloud Identities',
    data: [
      {
        id: 'unused',
        label: 'Unused',
        value: 38
      },
      {
        id: 'used',
        label: 'Used',
        value: 50
      },
      {
        id: 'dimissed',
        label: 'Dimissed',
        value: 12
      }
    ]
  },
  {
    labelTitle: '50%',
    labelDescription: 'Are Unused Actions',
    title: 'Cloud Actions',
    data: [
      {
        id: 'unused',
        label: 'Unused',
        value: 50
      },
      {
        id: 'used',
        label: 'Used',
        value: 25
      },
      {
        id: 'dimissed',
        label: 'Dimissed',
        value: 25
      }
    ]
  },
  {
    labelTitle: '8%',
    labelDescription: 'Are Unused Access Keys',
    title: 'Access Keys',
    data: [
      {
        id: 'unused',
        label: 'Unused',
        value: 8
      },
      {
        id: 'used',
        label: 'Used',
        value: 90
      },
      {
        id: 'dimissed',
        label: 'Dimissed',
        value: 2
      }
    ]
  },
  {
    labelTitle: '15%',
    labelDescription: 'Are Unused Console Passwords',
    title: 'Console Passwords',
    data: [
      {
        id: 'unused',
        label: 'Unused',
        value: 15
      },
      {
        id: 'used',
        label: 'Used',
        value: 80
      },
      {
        id: 'dimissed',
        label: 'Dimissed',
        value: 5
      }
    ]
  },
  {
    labelTitle: '11%',
    labelDescription: 'Are Passwords without MFA',
    title: 'Multi-factor Authentication',
    data: [
      {
        id: 'without_mfa',
        label: 'Without MFA',
        value: 11
      },
      {
        id: 'with_mfa',
        label: 'With MFA',
        value: 85
      },
      {
        id: 'dimissed',
        label: 'Dimissed',
        value: 4
      }
    ]
  }
];

const currentDate = new Date();

const generateDataPoint = (previousValue, trend = 'up') => {
  const randomChange = Math.floor(Math.random() * 10);
  if (trend === 'up') {
    return previousValue + randomChange;
  } else {
    return Math.max(previousValue - randomChange, 0);
  }
};

let previousUnusedValue = 100;
let previousDismissedValue = 10;

export const cleanupProgressMetricsData = [
  {
    title: 'Unused Cloud Actions',
    description: '85% less than when you first started using Noq',
    data: [
      {
        id: 'unused_actions',
        label: 'Unused actions',
        data: Array.from({ length: 12 }, (_, i) => {
          const value = generateDataPoint(previousUnusedValue, 'down');
          previousUnusedValue = value;
          return {
            x: new Date(
              currentDate.getFullYear(),
              currentDate.getMonth() - i
            ).toLocaleDateString('en-US', {
              month: '2-digit',
              year: '2-digit'
            }),
            y: value
          };
        }).reverse()
      },
      {
        id: 'dismissed_actions',
        label: 'Dismissed actions',
        data: Array.from({ length: 12 }, (_, i) => {
          const value = generateDataPoint(previousDismissedValue, 'up');
          previousDismissedValue = value;
          return {
            x: new Date(
              currentDate.getFullYear(),
              currentDate.getMonth() - i
            ).toLocaleDateString('en-US', {
              month: '2-digit',
              year: '2-digit'
            }),
            y: value
          };
        }).reverse()
      }
    ]
  },
  {
    title: 'Unused Cloud Identities',
    description: '85% less than when you first started using Noq',
    data: [
      {
        id: 'unused_actions',
        label: 'Unused actions',
        data: Array.from({ length: 12 }, (_, i) => {
          const value = generateDataPoint(previousUnusedValue, 'down');
          previousUnusedValue = value;
          return {
            x: new Date(
              currentDate.getFullYear(),
              currentDate.getMonth() - i
            ).toLocaleDateString('en-US', {
              month: '2-digit',
              year: '2-digit'
            }),
            y: value
          };
        }).reverse()
      },
      {
        id: 'dismissed_actions',
        label: 'Dismissed actions',
        data: Array.from({ length: 12 }, (_, i) => {
          const value = generateDataPoint(previousDismissedValue, 'up');
          previousDismissedValue = value;
          return {
            x: new Date(
              currentDate.getFullYear(),
              currentDate.getMonth() - i
            ).toLocaleDateString('en-US', {
              month: '2-digit',
              year: '2-digit'
            }),
            y: value
          };
        }).reverse()
      }
    ]
  }
];
