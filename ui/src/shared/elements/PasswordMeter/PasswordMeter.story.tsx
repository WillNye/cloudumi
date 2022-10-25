import { useState } from 'react';
import { PasswordMeter } from './PasswordMeter';

export default {
  title: 'Form/Password Meter',
  component: PasswordMeter
};

export const Basic = () => {
  const [value, setValue] = useState('');
  return (
    <>
      <input onChange={e => setValue(e.target.value)} />
      <PasswordMeter value={value} />
    </>
  );
};
