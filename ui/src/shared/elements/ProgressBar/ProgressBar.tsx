import classNames from 'classnames';
import styles from './ProgressBar.module.css';
import { useMemo } from 'react';

type ProgressBarProps = {
  percentage: number;
  size?: 'small' | 'medium' | 'large';
  color?: 'secondary' | 'primary' | 'danger' | 'warning' | 'success';
};

const ProgressBar = ({
  percentage,
  size = 'small',
  color = 'primary'
}: ProgressBarProps) => {
  const progressBarClasses = useMemo(
    () =>
      classNames(styles.progressBar, {
        [styles[size]]: size
      }),
    [size]
  );

  const progressBarFillClasses = useMemo(
    () =>
      classNames(styles.progressFill, {
        [styles[color]]: color
      }),
    [color]
  );

  return (
    <div className={progressBarClasses}>
      <div
        className={progressBarFillClasses}
        style={{ width: `${percentage}%` }}
      ></div>
    </div>
  );
};

export default ProgressBar;
