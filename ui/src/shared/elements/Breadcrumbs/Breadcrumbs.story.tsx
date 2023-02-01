import { Breadcrumbs } from './Breadcrumbs';

export default {
  title: 'Elements/Breadcrumbs',
  component: Breadcrumbs
};

const items = [
  { id: '1', name: 'Home', url: '/home' },
  { id: '2', name: 'About', url: '/about' },
  { id: '3', name: 'Contact', url: '/contact' }
];

export const Basic = () => <Breadcrumbs items={items} />;
