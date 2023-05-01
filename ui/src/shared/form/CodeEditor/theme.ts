import { editor } from 'monaco-editor';

export const darkTheme = (): editor.IStandaloneThemeData => ({
  base: 'vs-dark',
  inherit: true,
  rules: [
    { token: 'variable.name', foreground: '#00ffc6' },
    { token: 'variable.other', foreground: '#00ffc6' }
  ],
  colors: {
    // 'editor.background': '#000000',
    // 'editor.lineHighlightBackground':'#cccccc'
  },
  encodedTokensColors: []
});
