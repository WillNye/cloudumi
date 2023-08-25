import { ReactNode } from 'react';
import classNames from 'classnames';
import styles from './Bullet.module.css';

type BulletProps = {
  color?: 'secondary' | 'primary' | 'danger' | 'warning' | 'success';
  label: ReactNode;
};

const Bullet = ({ label, color = 'primary' }: BulletProps) => {
  const bulletClassName = classNames(styles.bulletPoint, {
    [styles[color]]: color
  });

  return (
    <div className={styles.bullet}>
      <span className={bulletClassName}></span> {label}
    </div>
  );
};

export default Bullet;
