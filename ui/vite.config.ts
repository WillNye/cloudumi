import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import eslint from 'vite-plugin-eslint';
import svgrPlugin from 'vite-plugin-svgr';
import tsconfigPaths from 'vite-tsconfig-paths';
import checker from 'vite-plugin-checker';

export default defineConfig(({ command }) => {
  const config = {
    plugins: [
      svgrPlugin(),
      tsconfigPaths(),
      react(),
      eslint(),
      checker({
        typescript: true
      })
    ],
    server: {
      port: 3000,
      open: true,
      host: '::',
    }
  };

  // Make CSS module names less annoying in dev mode
  if (command === 'serve') {
    // @ts-ignore
    config.css = {
      modules: {
        generateScopedName: '[name]-[local]'
      }
    };
  }

  return config;
});