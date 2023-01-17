import { useState } from 'react';
import { Checkbox } from './Checkbox';

export default {
  title: 'Form/Checkbox',
  component: Checkbox
};

export const Basic = () => {
  const [isSelected, setIsSelected] = useState(false);
  return <Checkbox />;
};
