import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import eslint from 'vite-plugin-eslint';
import svgrPlugin from 'vite-plugin-svgr';
import tsconfigPaths from 'vite-tsconfig-paths';
import checker from 'vite-plugin-checker';
import fs from 'fs';

export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, process.cwd());

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
    define: {
      // AWS Amplify throws error about global undefined
      // Reference: https://github.com/vitejs/vite/discussions/5912#discussioncomment-2908994
      global: {}
    },
    server: {
      port: 3000,
      open: true,
      host: '127.0.0.1',
      https: {
        // Reference: https://stackoverflow.com/questions/69417788/vite-https-on-localhost
        key: fs.readFileSync('./.certs/server.key.pem'),
        cert: fs.readFileSync('./.certs/server.pem')
      },
      proxy: {
        '/auth': {
          target: env.VITE_API_URL,
          changeOrigin: false
        },
        '/noauth': {
          target: env.VITE_API_URL,
          changeOrigin: false
        },
        '/saml': {
          target: env.VITE_API_URL,
          changeOrigin: false
        },
        '/api': {
          target: env.VITE_API_URL,
          changeOrigin: false
        },
        '/docs': {
          target: env.VITE_API_URL,
          changeOrigin: false
        }
      }
    },
    test: {
      globals: true,
      environment: 'happy-dom',
      coverage: {
        reporter: ['text', 'json', 'html'],
        all: true,
        include: ['src/**/*']
      }
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
