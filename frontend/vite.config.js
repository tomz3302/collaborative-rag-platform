// vite.config.js
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  const env = loadEnv(mode, process.cwd(), '');
  const apiUrl = env.VITE_API_URL || 'http://localhost:8000';

  return {
    plugins: [react()],

    server: {
      port: 3000,

      proxy: {
        '/api': {
          target: apiUrl,
          changeOrigin: true,
          secure: false,
        },
        '/auth': {
          target: apiUrl,
          changeOrigin: true,
          secure: false,
        },
        '/users': {
          target: apiUrl,
          changeOrigin: true,
          secure: false,
        }
      }
    }
  };
});