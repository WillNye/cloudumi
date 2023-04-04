import classNames from 'classnames';
import { ReactNode, Ref, forwardRef } from 'react';

import css from './Select.module.css';

export interface SelectProps
  extends Omit<
    React.SelectHTMLAttributes<HTMLSelectElement>,
    'suffix' | 'prefix' | 'size' | 'results'
  > {
  fullWidth?: boolean;
  selectOnFocus?: boolean;
  error?: boolean;
  containerClassname?: string;
  size?: 'small' | 'medium' | 'large';
  prefix?: React.ReactNode | string;
  suffix?: React.ReactNode | string;
  showBorder?: boolean;
  onClear?: () => void;
  children?: ReactNode;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      className,
      children,
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
      showBorder,
      onFocus,
      ...rest
    },
    ref: Ref<HTMLSelectElement>
  ) => (
    <span
      className={classNames(css.container, containerClassname, {
        [css.fullWidth]: fullWidth,
        [css.error]: error,
        [css[size]]: size,
        [css.disabled]: disabled,
        [css.showBorder]: showBorder
      })}
    >
      {prefix && <div className={css.prefix}>{prefix}</div>}
      <select
        {...rest}
        ref={ref}
        value={value}
        disabled={disabled}
        className={classNames(className, css.select)}
      >
        {children}
      </select>
      {suffix && <div className={css.suffix}>{suffix}</div>}
    </span>
  )
);
