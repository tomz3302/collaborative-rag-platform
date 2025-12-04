// vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],

  // 1. ADD THE 'server' BLOCK HERE
  server: {
    // We set the frontend port to 3000 to avoid conflicting with the backend
    port: 3000,

    // 2. NEST THE proxy configuration inside 'server'
    proxy: {
      '/api': {
        target: 'http://localhost:8000', // Using 8000 as specified
        changeOrigin: true,
        secure: false,
      }
    }
  }
});