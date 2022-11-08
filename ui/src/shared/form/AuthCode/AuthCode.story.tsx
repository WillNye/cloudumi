import { AuthCode } from './AuthCode';

export default {
  title: 'Form/AuthCode',
  component: AuthCode
};

export const Defaults = () => <AuthCode onChange={val => console.log(val)} />;

export const CharacterLimit = () => (
  <AuthCode length={10} onChange={val => console.log(val)} />
);

export const NumbersOnly = () => (
  <AuthCode allowedCharacters="numeric" onChange={val => console.log(val)} />
);

export const HideValues = () => (
  <AuthCode password onChange={val => console.log(val)} />
);
