import { DocsContainer } from '@storybook/addon-docs';
import { darkTheme } from './theme';

export const parameters = {
  layout: 'centered',
  actions: { argTypesRegex: "^on[A-Z].*" },
  docs: {
    theme: darkTheme,
    container: ({ context, children }) => (
      <DocsContainer context={context}>
        {children}
      </DocsContainer>
    ),
  },
  controls: {
    matchers: {
      color: /(background|color)$/i,
      date: /Date$/,
    },
  },
}
