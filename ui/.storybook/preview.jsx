import { DocsContainer } from '@storybook/addon-docs';
import { BrowserRouter } from 'react-router-dom';
import { DesignTokensProvider } from 'reablocks';

import { storybookTheme } from './theme';
import { theme } from '../src/shared/utils/DesignTokens';

import '../src/index.css';

const withProvider = (Story, context) => (
  <BrowserRouter>
    <DesignTokensProvider theme={theme}>
      <Story {...context} />
    </DesignTokensProvider>
  </BrowserRouter>
);

export const decorators = [withProvider];

export const parameters = {
  layout: 'centered',
  actions: { argTypesRegex: '^on[A-Z].*' },
  docs: {
    theme: storybookTheme,
    container: ({ context, children }) => (
      <DocsContainer context={context}>
        <DesignTokensProvider theme={theme}>
          {children}
        </DesignTokensProvider>
      </DocsContainer>
    )
  },
  controls: {
    hideNoControlsWarning: true
  }
};
