import React, { FC, forwardRef, Ref } from 'react';
import classNames from 'classnames';
import { motion } from 'framer-motion';
import css from './Button.module.css';
import { Icon } from '../Icon';

export interface ButtonProps
  extends Omit<
    React.ButtonHTMLAttributes<HTMLButtonElement>,
    'onAnimationStart' | 'onDragStart' | 'onDragEnd' | 'onDrag'
  > {
  color?: 'default' | 'primary' | 'secondary' | 'error';
  variant?: 'filled' | 'outline' | 'text';
  fullWidth?: boolean;
  disableMargins?: boolean;
  disablePadding?: boolean;
  disableAnimation?: boolean;
  size?: 'small' | 'medium' | 'large';
  icon?: string;
}

export interface ButtonRef {
  ref?: Ref<HTMLButtonElement>;
}

export const Button: FC<ButtonProps & ButtonRef> = forwardRef(
  (
    {
      color = 'primary',
      variant = 'filled',
      children,
      type,
      fullWidth,
      size = 'medium',
      icon,
      className,
      disableMargins,
      disableAnimation,
      disablePadding,
      disabled,
      ...rest
    }: ButtonProps,
    ref: Ref<HTMLButtonElement>
  ) => (
    <motion.button
      {...rest}
      disabled={disabled}
      ref={ref}
      whileTap={{ scale: disabled || disableAnimation ? 1 : 0.9 }}
      type={type || 'button'}
      className={classNames(className, css.btn, {
        [css.fullWidth]: fullWidth,
        [css[size]]: size,
        [css[color]]: color,
        [css[variant]]: variant,
        [css.disableMargins]: disableMargins,
        [css.disablePadding]: disablePadding
      })}
    >
      {children}
      {icon && <Icon className={css.icon} name={icon} size={size} />}
    </motion.button>
  )
);
