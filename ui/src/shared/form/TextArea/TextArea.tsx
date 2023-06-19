import React, { FC, forwardRef, Ref } from 'react';
import classNames from 'classnames';
import css from './TextArea.module.css';

export interface TextAreaProps
  extends Omit<
    React.TextareaHTMLAttributes<HTMLTextAreaElement>,
    'suffix' | 'prefix' | 'size' | 'results'
  > {
  fullWidth?: boolean;
  selectOnFocus?: boolean;
  error?: boolean;
  containerClassname?: string;
  onClear?: () => void;
}

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(
  (
    {
      className,
      selectOnFocus,
      containerClassname,
      fullWidth,
      disabled,
      value,
      error,
      rows = 4,
      onFocus,
      ...rest
    },
    ref: Ref<HTMLTextAreaElement>
  ) => (
    <span
      className={classNames(css.container, containerClassname, {
        [css.fullWidth]: fullWidth,
        [css.error]: error,
        [css.disabled]: disabled
      })}
    >
      <textarea
        {...rest}
        ref={ref}
        value={value}
        rows={rows}
        disabled={disabled}
        className={classNames(className, css.textarea)}
        onFocus={event => {
          if (selectOnFocus) {
            event.target.select();
          }
          onFocus?.(event);
        }}
      />
    </span>
  )
);

export default TextArea;
