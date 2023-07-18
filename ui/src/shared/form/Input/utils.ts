export const transformStringIntoArray = {
  input: (value: string[]) => value.join(','),
  output: e => (e.target.value ?? '').replaceAll(' ', '').split(',')
};
