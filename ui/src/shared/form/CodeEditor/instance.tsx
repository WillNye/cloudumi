import { darkTheme } from './theme';
import { Monaco } from '@monaco-editor/react';

export function setupEditor(
  instance: Monaco
) {
  // This is a function so we can variables in the future
  const theme = darkTheme();

  // Set our special theme
  instance.editor.defineTheme('noq', theme);
  instance.editor.setTheme('noq');
}
