import { defineConfig } from 'cypress';

export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost:8092',
    setupNodeEvents(on, config) {
      on('task', {
        log(message) {
          console.log(message);

          return null;
        }
      });
    }
  },
  browserLaunchOptions: {
    args: ['--disable-gpu']
  },
  defaultCommandTimeout: 10000
});
