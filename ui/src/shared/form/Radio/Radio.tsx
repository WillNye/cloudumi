import { FC } from 'react';
import styles from './Radio.module.css';
import { BaseInput, BaseInputProps } from '../Input';

export const Radio: FC<BaseInputProps> = props => {
  return (
    <div className={styles.container}>
      <BaseInput {...props} type="radio" />
    </div>
  );
};
