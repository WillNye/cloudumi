import classNames from 'classnames';
import styles from './Chip.module.css';
import { ReactNode } from 'react';

export type ChipProps = {
  children?: ReactNode;
  type?: ChipType;
  className?: string;
};

export type ChipType =
  | 'default'
  | 'primary'
  | 'secondary'
  | 'success'
  | 'danger'
  | 'warning'
  | 'info'
  | 'light'
  | 'dark';

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
