import { FC, ReactNode } from 'react';

import styles from './Notification.module.css';
import { Icon } from '../Icon';
import classNames from 'classnames';

export enum NotificationType {
  ERROR = 'error',
  SUCCESS = 'success',
  INFO = 'info',
  WARNING = 'warning'
}

export enum NotificationPosition {
  EMBEDDED = 'embedded',
  FLOATING = 'floating'
}

interface NotificationProps {
  type?: NotificationType;
  message?: string;
  header: string;
  children?: ReactNode;
  onClose?: () => void;
  showCloseIcon?: boolean;
  fullWidth?: boolean;
  position?: NotificationPosition;
}

export const Notification: FC<NotificationProps> = ({
  type,
  message,
  header,
  children,
  showCloseIcon = true,
  onClose,
  fullWidth,
  position = NotificationPosition.EMBEDDED
}) => {
  return (
    <div
      className={classNames(styles.notification, {
        [styles.fullWidth]: fullWidth,
        [styles.floating]: position === NotificationPosition.FLOATING
      })}
    >
      {type && (
        <Icon name={`notification-${type}`} color="primary" size="large" />
      )}
      <div className={styles.content}>
        <div className={styles.header}>{header}</div>
        {message && <p className={styles.text}>{message}</p>}
        {children}
      </div>
      {showCloseIcon && (
        <div className={styles.close} onClick={onClose}>
          <Icon name="close" color="secondary" size="large" />
        </div>
      )}
    </div>
  );
};
