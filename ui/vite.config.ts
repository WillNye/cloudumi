import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import eslint from 'vite-plugin-eslint';
import svgrPlugin from 'vite-plugin-svgr';
import tsconfigPaths from 'vite-tsconfig-paths';
import checker from 'vite-plugin-checker';
import fs from 'fs';

export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, process.cwd());

  const plugins = [
    svgrPlugin(),
    tsconfigPaths(),
    react(),
    checker({
      typescript: true
    })
  ];

  if (mode !== 'production') {
    plugins.push(eslint());
  }

  const config = {
    plugins,
    server: {
      port: 3000,
      open: true,
      host: '127.0.0.1',
      https:
        command === 'serve'
          ? {
              key: fs.readFileSync('./.certs/server.key.pem'),
              cert: fs.readFileSync('./.certs/server.pem')
            }
          : undefined,
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
        },
        '/aws_marketplace': {
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

  if (command === 'serve') {
    config.css = {
      modules: {
        generateScopedName: '[name]-[local]'
      }
    };
  }

  return config;
});
