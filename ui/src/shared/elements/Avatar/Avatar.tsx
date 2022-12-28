import { useMemo } from 'react';
import styles from './Avatar.module.css';

type AvatarProps = {
  src?: string;
  name?: string;
  size?: 'small' | 'medium' | 'large';
};

export const Avatar = ({ src, name, size = 'medium' }: AvatarProps) => {
  const nameIntial = useMemo(() => {
    if (name) {
      return name.charAt(0).toUpperCase();
    }
    return '';
  }, [name]);

  return (
    <div className={`${styles.avatar} ${styles[size]}`}>
      {src ? (
        <img src={src} alt={name} />
      ) : (
        <div className={styles.text}>{nameIntial}</div>
      )}
    </div>
  );
};
