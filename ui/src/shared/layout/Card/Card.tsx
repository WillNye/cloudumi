import React, { forwardRef, Ref, FC } from 'react';
import classNames from 'classnames';
import css from './Card.module.css';

export interface CardProps extends React.DOMAttributes<any> {
  disablePadding?: boolean;
  className?: string;
  headerClassName?: string;
  contentClassName?: string;
  style?: React.CSSProperties;
  header?: string | JSX.Element | JSX.Element[];
  variant?: 'outlined';
  clickable?: boolean;
  color?: 'default' | 'primary' | 'secondary' | 'danger' | 'warning';
}

export const Card: FC<CardProps & { ref?: Ref<HTMLDivElement> }> = forwardRef(
  (
    {
      children,
      disablePadding,
      className,
      header,
      headerClassName,
      contentClassName,
      variant,
      clickable = false,
      color = 'default',
      ...rest
    }: CardProps,
    ref: Ref<HTMLDivElement>
  ) => {
    return (
      <section
        {...rest}
        ref={ref}
        className={classNames(className, css.card, {
          [css.disablePadding]: disablePadding,
          [css.outlined]: variant === 'outlined',
          [css.default]: color === 'default',
          [css.danger]: color === 'danger',
          [css.secondary]: color === 'secondary',
          [css.primary]: color === 'primary',
          [css.warning]: color === 'warning',
          [css.clickable]: clickable
        })}
      >
        {header && (
          <header className={classNames(css.header, headerClassName)}>
            <h3 className={css.headerText}>{header}</h3>
          </header>
        )}
        <div className={classNames(css.content, contentClassName)}>
          {children}
        </div>
      </section>
    );
  }
);
