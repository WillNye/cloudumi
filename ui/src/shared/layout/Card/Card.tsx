import React, { forwardRef, Ref, FC, useState, useRef, Fragment } from 'react';
import classNames from 'classnames';
import css from './Card.module.css';

export interface CardProps extends React.DOMAttributes<any> {
  disablePadding?: boolean;
  className?: string;
  headerClassName?: string;
  contentClassName?: string;
  style?: React.CSSProperties;
  header?: string | JSX.Element | JSX.Element[];
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
      ...rest
    }: CardProps,
    ref: Ref<HTMLDivElement>
  ) => {
    const [menuOpen, setMenuOpen] = useState<boolean>(false);
    const menuRef = useRef<HTMLButtonElement | null>(null);

    return (
      <section
        {...rest}
        ref={ref}
        className={classNames(className, css.card, {
          [css.disablePadding]: disablePadding
        })}
      >
        {header && (
          <header className={classNames(css.header, headerClassName)}>
            {header && <h3 className={css.headerText}>{header}</h3>}
          </header>
        )}
        <div className={classNames(css.content, contentClassName)}>
          {children}
        </div>
      </section>
    );
  }
);
