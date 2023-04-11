import { Select } from './Select';
import { SelectOption } from './SelectOption';

export default {
  title: 'Form/Select',
  component: Select
};

export const Basic = () => (
  <Select>
    <SelectOption value="1">1</SelectOption>
    <SelectOption value="2">2</SelectOption>
    <SelectOption value="3">3</SelectOption>
    <SelectOption value="4">4</SelectOption>
    <SelectOption value="5">5</SelectOption>
  </Select>
);
