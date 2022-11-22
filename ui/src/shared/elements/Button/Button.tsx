import React, { FC, forwardRef, Ref } from 'react';
import classNames from 'classnames';
import { motion } from 'framer-motion';
import css from './Button.module.css';

export interface ButtonProps
  extends Omit<
    React.ButtonHTMLAttributes<HTMLButtonElement>,
    'onAnimationStart' | 'onDragStart' | 'onDragEnd' | 'onDrag'
  > {
  // Examples on how to use color/variants...
  color?: 'default' | 'primary' | 'secondary' | 'error';
  variant?: 'filled' | 'outline' | 'text';
  fullWidth?: boolean;
  disableMargins?: boolean;
  disablePadding?: boolean;
  disableAnimation?: boolean;
  size?: 'small' | 'medium' | 'large';
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

        [css.primary]: color === 'primary',
        [css.secondary]: color === 'secondary',
        [css.error]: color === 'error',

        [css.small]: size === 'small',
        [css.medium]: size === 'medium',
        [css.large]: size === 'large',

        [css.filled]: variant === 'filled',
        [css.outline]: variant === 'outline',
        [css.text]: variant === 'text',

        [css.disableMargins]: disableMargins,
        [css.disablePadding]: disablePadding
      })}
    >
      {children}
    </motion.button>
  )
);
