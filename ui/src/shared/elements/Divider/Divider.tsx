import React, { FC } from 'react';
import classNames from 'classnames';
import css from './Divider.module.css';

export interface DividerProps {
  className?: string;
  disableMargins?: boolean;
  orientation?: 'horizontal' | 'vertical';
  style?: React.CSSProperties;
}

export const Divider: FC<DividerProps> = ({
  className,
  disableMargins,
  orientation = 'horizontal',
  ...rest
}) => (
  <hr
    {...rest}
    className={classNames(css.divider, className, {
      [css.disableMargins]: disableMargins,
      [css[orientation]]: orientation
    })}
  />
);
