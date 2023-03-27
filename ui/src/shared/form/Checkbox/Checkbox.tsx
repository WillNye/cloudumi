import React, { FC, forwardRef, ReactNode, Ref } from 'react';
import classNames from 'classnames';
import { BaseInput } from '../Input';
import css from './Checkbox.module.css';

export interface CheckboxProps
  extends Omit<
    React.InputHTMLAttributes<HTMLInputElement>,
    'suffix' | 'prefix' | 'size'
  > {
  error?: boolean;
  containerClassname?: string;
  prefix?: ReactNode;
  suffix?: ReactNode;
  size?: 'small' | 'medium' | 'large';
  onClear?: () => void;
}

export const Checkbox: FC<CheckboxProps> = forwardRef(
  (
    {
      className,
      containerClassname,
      error,
      disabled,
      checked,
      prefix,
      suffix,
      size = 'small',
      ...rest
    },
    ref: Ref<HTMLInputElement>
  ) => {
    return (
      <span
        className={classNames(css.container, containerClassname, {
          [css.error]: error,
          [css[size]]: size,
          [css.disabled]: disabled
        })}
      >
        {prefix && <div className={css.prefix}>{prefix}</div>}
        <BaseInput
          {...rest}
          type="checkbox"
          ref={ref}
          checked={checked}
          disabled={disabled}
          className={classNames(className, css.input)}
        />
        {suffix && <div className={css.suffix}>{suffix}</div>}
      </span>
    );
  }
);
