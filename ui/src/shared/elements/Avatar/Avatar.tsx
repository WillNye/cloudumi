import { Ref, forwardRef, useMemo } from 'react';
import styles from './Avatar.module.css';
import classNames from 'classnames';

interface AvatarProps
  extends Omit<
    React.HTMLAttributes<HTMLDivElement>,
    'onAnimationStart' | 'onDragStart' | 'onDragEnd' | 'onDrag'
  > {
  src?: string;
  name?: string;
  size?: 'small' | 'medium' | 'large';
}

export const Avatar = forwardRef(
  (
    { src, name, className, size = 'medium', ...props }: AvatarProps,
    ref: Ref<HTMLDivElement>
  ) => {
    const nameIntial = useMemo(() => {
      if (name) {
        return name.charAt(0).toUpperCase();
      }
      return '';
    }, [name]);

    return (
      <div
        ref={ref}
        {...props}
        className={classNames(styles.avatar, className, {
          [styles[size]]: size
        })}
      >
        {src ? (
          <img src={src} alt={name} />
        ) : (
          <div className={styles.text}>{nameIntial}</div>
        )}
      </div>
    );
  }
);
