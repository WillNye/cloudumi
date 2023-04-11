import { FC } from 'react';
import css from './Select.module.css';

export const SelectOption: FC<
  React.OptionHTMLAttributes<HTMLOptionElement>
> = ({ className, children, ...rest }) => (
  <option {...rest} className={css.option}>
    {children}
  </option>
);
