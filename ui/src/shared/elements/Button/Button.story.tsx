import { DesignTokensProvider } from 'reablocks';
import { theme } from 'shared/utils/DesignTokens';
import { Button } from './Button';

export default {
  title: 'Elements/Button',
  component: Button
};

export const Variants = () => (
  <DesignTokensProvider value={theme}>
    <Button variant="filled">Small</Button>
    <Button variant="outline" color="secondary">
      Medium
    </Button>
    <Button variant="text" color="primary">
      Large
    </Button>
  </DesignTokensProvider>
);

export const Colors = () => (
  <DesignTokensProvider value={theme}>
    <Button color="primary">Primary</Button>
    <Button color="secondary">Secondary</Button>
    <Button color="error">Error</Button>
  </DesignTokensProvider>
);

export const Sizes = () => (
  <DesignTokensProvider value={theme}>
    <Button size="small">Small</Button>
    <Button size="medium">Medium</Button>
    <Button size="large">Large</Button>
  </DesignTokensProvider>
);
