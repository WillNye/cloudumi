import { FC, MutableRefObject, useEffect, useState } from 'react';
import Code from 'react-auth-code-input';
import classNames from 'classnames';
import { nanoid } from 'nanoid';
import css from './AuthCode.module.css';

export interface AuthCodeInput {
  length?: number;
  password?: boolean;
  inputClassName?: string;
  autoFocus?: boolean;
  containerClassName?: string;
  allowedCharacters?: 'alphanumeric' | 'alpha' | 'numeric';
  disabled?: boolean;
  onChange: (val: string) => void;
  onReset?: MutableRefObject<() => void>;
}

export const AuthCode: FC<AuthCodeInput> = ({
  inputClassName,
  length = 6,
  containerClassName,
  allowedCharacters = 'numeric',
  onReset,
  ...rest
}) => {
  const [authKey, setAuthKey] = useState<string>(nanoid());

  useEffect(() => {
    // react-auth-code-input does not allow uncontrolled components and does not have a reset value
    // function. So in order to reset the value on an invalid 2FA value, we need to remount the
    // component https://github.com/drac94/react-auth-code-input/issues/15
    if (onReset) {
      onReset.current = () => {
        setAuthKey(nanoid());
      };
    }
  }, [onReset]);

  return (
    <Code
      key={authKey}
      allowedCharacters={allowedCharacters}
      length={length}
      {...rest}
      inputClassName={classNames(css.input, inputClassName)}
      containerClassName={classNames(css.authCode, containerClassName)}
    />
  );
};
