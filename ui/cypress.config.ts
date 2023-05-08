import { defineConfig } from 'cypress';

export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost:8092',
    setupNodeEvents(on, config) {
      // implement node event listeners here
    }
  },
  browserLaunchOptions: {
    args: ['--disable-gpu']
  },
  defaultCommandTimeout: 10000
});
