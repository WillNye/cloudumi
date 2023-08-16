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

export const lineMockData = [
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
        ).toLocaleDateString('en-US', { month: '2-digit', year: '2-digit' }),
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
        ).toLocaleDateString('en-US', { month: '2-digit', year: '2-digit' }),
        y: value
      };
    }).reverse()
  }
];
