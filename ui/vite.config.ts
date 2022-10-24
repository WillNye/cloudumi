import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import eslint from 'vite-plugin-eslint';
import svgrPlugin from 'vite-plugin-svgr';
import tsconfigPaths from 'vite-tsconfig-paths';
import checker from 'vite-plugin-checker';
import fs from 'fs';

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
      https: {
        // Reference: https://stackoverflow.com/questions/69417788/vite-https-on-localhost
        key: fs.readFileSync('./.certs/server.key.pem'),
        cert: fs.readFileSync('./.certs/server.pem'),
      },
      proxy: {
        '/api': {
          // TODO: Put this in ENV variables
          target: 'http://localhost:8092',
          // changeOrigin: true,
          // secure: false
        }
      }
    },
    test: {
      globals: true,
      environment: 'jsdom'
    }
  };

  // Make CSS module names less annoying in dev mode
  if (command === 'serve') {
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    config.css = {
      modules: {
        generateScopedName: '[name]-[local]'
      }
    };
  }

  return config;
});
