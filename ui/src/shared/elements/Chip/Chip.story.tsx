import { Chip } from './Chip';

export default {
  title: 'Elements/Chip',
  component: Chip
};

export const Basic = () => {
  return (
    <div>
      <Chip>Default</Chip>
      <Chip type="primary">Primary</Chip>
      <Chip type="secondary">Secondary</Chip>
      <Chip type="success">Success</Chip>
      <Chip type="danger">Danger</Chip>
      <Chip type="warning">Warning</Chip>
      <Chip type="info">Info</Chip>
      <Chip type="light">Light</Chip>
      <Chip type="dark">Dark</Chip>
    </div>
  );
};
