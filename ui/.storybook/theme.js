import { create } from '@storybook/theming';
import Logo from '../src/assets/brand/logo-bw.svg';

export const darkTheme = create({
  brandImage: Logo,
  base: 'dark',
  brandTitle: 'NOQ'
});
