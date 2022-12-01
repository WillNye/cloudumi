import React, {
  FC,
  forwardRef,
  Ref,
  RefObject,
  useImperativeHandle,
  useLayoutEffect,
  useRef
} from 'react';
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

export interface InputRef {
  inputRef: RefObject<HTMLInputElement>;
  containerRef: RefObject<HTMLDivElement>;
  blur?: () => void;
  focus?: () => void;
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
      size = 'medium',
      onFocus,
      ...rest
    },
    ref: Ref<InputRef>
  ) => {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const inputRef = useRef<HTMLInputElement | null>(null);

    useImperativeHandle(ref, () => ({
      inputRef,
      containerRef,
      blur: () => inputRef.current?.blur(),
      focus: () => inputRef.current?.focus()
    }));

    useLayoutEffect(() => {
      if (autoFocus) {
        // Small timeout for page loading
        setTimeout(() => inputRef.current?.focus());
      }
    }, [autoFocus]);

    return (
      <div
        className={classNames(css.container, containerClassname, {
          [css.fullWidth]: fullWidth,
          [css.error]: error
          // [css.small]: size === 'small',
          // [css.medium]: size === 'medium'
        })}
        ref={containerRef}
      >
        {prefix && <div className={css.prefix}>{prefix}</div>}
        <input
          {...rest}
          ref={inputRef}
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
      </div>
    );
  }
);
