import { Button } from './Button';

export default {
  title: 'Elements/Button',
  component: Button
};

export const Variants = () => (
  <>
    <Button variant="filled">Filled</Button>
    {'  '}
    <Button variant="outline" color="secondary">
      Outline
    </Button>
    {'  '}
    <Button variant="text" color="primary">
      Text
    </Button>
  </>
);

export const Colors = () => (
  <>
    <Button color="primary">Primary</Button>
    {'  '}
    <Button color="secondary">Secondary</Button>
    {'  '}
    <Button color="error">Error</Button>
  </>
);

export const Sizes = () => (
  <>
    <Button size="small">Small</Button>
    {'  '}
    <Button size="medium">Medium</Button>
    {'  '}
    <Button size="large">Large</Button>
  </>
);

export const IconButton = () => (
  <>
    <Button size="small" icon="pending">
      Small
    </Button>
    {'  '}
    <Button icon="signin">Medium</Button>
    {'  '}
    <Button icon="recents" size="large" />
  </>
);
