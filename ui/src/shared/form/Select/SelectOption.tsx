import { FC } from 'react';
import css from './Select.module.css';
import classNames from 'classnames';

export const SelectOption: FC<
  React.OptionHTMLAttributes<HTMLOptionElement>
> = ({ className, children, ...rest }) => (
  <option {...rest} className={classNames(className, css.option)}>
    {children}
  </option>
);
