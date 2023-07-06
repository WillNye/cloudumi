import classNames from 'classnames';
import styles from './Chip.module.css';
import { ReactNode } from 'react';

type ChipProps = {
  children?: ReactNode;
  type?:
    | 'default'
    | 'primary'
    | 'secondary'
    | 'success'
    | 'danger'
    | 'warning'
    | 'info'
    | 'light'
    | 'dark';
  className?: string;
};

export const Chip = ({
  children,
  type = 'default',
  className = ''
}: ChipProps) => {
  return (
    <span className={classNames(styles.badge, className, styles[type])}>
      {children}
    </span>
  );
};
