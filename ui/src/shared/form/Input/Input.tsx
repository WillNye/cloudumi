import React, { FC, forwardRef, Ref } from 'react';
import classNames from 'classnames';
import css from './Input.module.css';
import { LineBreak } from 'shared/elements/LineBreak';

export interface InputProps
  extends Omit<
    React.InputHTMLAttributes<HTMLInputElement>,
    'suffix' | 'prefix' | 'size' | 'results'
  > {
  fullWidth?: boolean;
  selectOnFocus?: boolean;
  error?: string | null;
  containerClassname?: string;
  size?: 'small' | 'medium' | 'large';
  prefix?: React.ReactNode | string;
  suffix?: React.ReactNode | string;
  showBorder?: boolean;
  onClear?: () => void;
}

export interface BaseInputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  fullWidth?: boolean;
  selectOnFocus?: boolean;
  showBorder?: boolean;
  onClear?: () => void;
}

export const BaseInput = forwardRef<HTMLInputElement, BaseInputProps>(
  (
    { className, selectOnFocus, disabled, value, onFocus, ...rest },
    ref: Ref<HTMLInputElement>
  ) => (
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
  )
);

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
      disabled,
      value,
      size = 'small',
      showBorder = true,
      onFocus,
      ...rest
    },
    ref: Ref<HTMLInputElement>
  ) => (
    <>
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
        <BaseInput
          {...rest}
          ref={ref}
          value={value}
          disabled={disabled}
          className={className}
          onFocus={event => {
            if (selectOnFocus) {
              event.target.select();
            }
            onFocus?.(event);
          }}
        />
        {suffix && <div className={css.suffix}>{suffix}</div>}
      </span>
      {error && (
        <>
          <LineBreak size="small" />
          <span
            className={classNames(css.errorContainer, {
              [css.fullWidth]: fullWidth
            })}
          >
            {error}
          </span>
        </>
      )}
    </>
  )
);
