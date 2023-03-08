import { Divider } from './Divider';

export default {
  title: 'Elements/Divider',
  component: Divider
};

export const Horizontal = () => <Divider style={{ width: 350 }} />;
export const Vertical = () => (
  <div style={{ height: 350, width: 50 }}>
    <Divider orientation="vertical" />
  </div>
);
