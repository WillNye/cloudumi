// BarChartRating.tsx
import React from 'react';
import styles from './BarChartRating.module.css';
import classNames from 'classnames';

type BarChartRatingProps = {
  color?: 'secondary' | 'primary' | 'danger' | 'warning' | 'success';
  activeBars: number;
};

const BarChartRating: React.FC<BarChartRatingProps> = ({
  activeBars,
  color = 'secondary'
}) => {
  const determineBarStyle = (index: number) => {
    if (index < activeBars) {
      return styles[`active${activeBars}`];
    }
    return '';
  };

  return (
    <div className={styles.barContainer}>
      {[...Array(5)].map((_, index) => (
        <div
          key={index}
          className={classNames(styles.bar, {
            [styles[`bar${index + 1}`]]: true,
            [determineBarStyle(index + 1)]: true,
            [styles[color]]: color
          })}
        ></div>
      ))}
    </div>
  );
};

export default BarChartRating;
