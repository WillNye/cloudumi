import React, { FC, forwardRef, Ref } from 'react';
import classNames from 'classnames';
import css from './Input.module.css';

export interface InputProps
  extends Omit<
    React.InputHTMLAttributes<HTMLInputElement>,
    'suffix' | 'prefix' | 'size'
  > {
  fullWidth?: boolean;
  selectOnFocus?: boolean;
  error?: boolean;
  containerClassname?: string;
  size?: 'small' | 'medium' | 'large';
  prefix?: React.ReactNode | string;
  suffix?: React.ReactNode | string;
  onClear?: () => void;
}

export const Input: FC<InputProps> = forwardRef(
  (
    {
      className,
      containerClassname,
      error,
      fullWidth,
      selectOnFocus,
      prefix,
      suffix,
      autoFocus,
      disabled,
      value,
      size = 'small',
      onFocus,
      ...rest
    },
    ref: Ref<HTMLInputElement>
  ) => {
    return (
      <span
        className={classNames(css.container, containerClassname, {
          [css.fullWidth]: fullWidth,
          [css.error]: error,
          [css[size]]: size,
          [css.disabled]: disabled
        })}
      >
        {prefix && <div className={css.prefix}>{prefix}</div>}
        <input
          {...rest}
          ref={ref}
          value={value}
          disabled={disabled}
          className={classNames(className, css.input)}
          onFocus={event => {
            if (selectOnFocus) {
              event.target.select();
            }
            onFocus?.(event);
          }}
        />
        {suffix && <div className={css.suffix}>{suffix}</div>}
      </span>
    );
  }
);
