import classNames from 'classnames';
import styles from './Chip.module.css';

export const Chip = ({ children, type = 'default' }) => {
  return (
    <span className={classNames(styles.badge, styles[type])}>{children}</span>
  );
};
