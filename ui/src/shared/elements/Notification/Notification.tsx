import classNames from 'classnames';
import { FC, ReactNode, useMemo } from 'react';
import { Button } from '../Button';

import styles from './Notification.module.css';
import { Icon } from '../Icon';

interface NotificationProps {
  type?: 'error' | 'success' | 'info' | 'warning';
  message: string;
  children: ReactNode;
}

export const Notification: FC<NotificationProps> = ({
  type,
  message,
  children
}) => {
  const classes = useMemo(() => {
    return classNames(styles.notification, {});
  }, []);

  return (
    <div className={classes}>
      <div>
        <Icon name="notification-info" color="primary" />
        <p>{message}</p>
        <Button icon="close" color="secondary" variant="outline"></Button>
      </div>
      {children}
    </div>
  );
};
