import { FC } from 'react';
import classNames from 'classnames';
import passwordMeter from 'passwordmeter';
import css from './PasswordMeter.module.css';

export interface PasswordMeterProps {
  value: string;
}

export const PasswordMeter: FC<PasswordMeterProps> = ({ value }) => {
  const strength = passwordMeter.checkPass(value);

  return (
    <div
      className={classNames(css.meter, {
        [css.weak]: strength > 0 && strength < 25,
        [css.medium]: strength >= 25 && strength < 50,
        [css.strong]: strength >= 50 && strength < 75,
        [css.veryStrong]: strength >= 75
      })}
    >
      <div />
      <div />
      <div />
      <div />
    </div>
  );
};
