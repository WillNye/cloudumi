import { FC, Fragment, useEffect, useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { checkPasswordComplexity } from 'core/API/auth';
import classNames from 'classnames';
import css from './PasswordMeter.module.css';

export interface PasswordMeterProps {
  value: string;
  fullWidth?: boolean;
}

const requirementHasError = (requirement, errors) => {
  const key = Object.keys(requirement)[0].toLowerCase();
  const value = Object.values(requirement)[0];
  const errorKey = `${key}(${value})`.toLowerCase();
  return errors.map(e => e.toLowerCase()).includes(errorKey);
};

export const PasswordMeter: FC<PasswordMeterProps> = ({
  value,
  fullWidth = false
}) => {
  const [passwordDetails, setPasswordDetails] = useState(null);

  const { mutateAsync: checkPasswordMutation } = useMutation({
    mutationFn: (password: string) => checkPasswordComplexity({ password }),
    mutationKey: ['checkPassword']
  });

  const requirements = useMemo(
    () => passwordDetails?.requirements ?? {},
    [passwordDetails]
  );
  const errors = useMemo(
    () => passwordDetails?.errors || [],
    [passwordDetails]
  );

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (!value) {
        setPasswordDetails(null);
        return;
      }
      const data = await checkPasswordMutation(value || ' ');
      setPasswordDetails(data?.data || null);
    }, 500);

    return () => {
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  if (!value) {
    return <Fragment />;
  }

  return (
    <div className={classNames(css.meter, { [css.fullWidth]: fullWidth })}>
      {Object.entries(requirements).map(([key, value]) => (
        <div
          key={key}
          className={`${
            requirementHasError({ [key]: value }, errors)
              ? css.weak
              : css.strong
          }`}
        >
          {`${key}: ${value}`}{' '}
          {requirementHasError({ [key]: value }, errors) ? '✘' : '✔'}
        </div>
      ))}
    </div>
  );
};
