import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const apiTarget = process.env.VITE_API_URL || 'http://localhost:8002'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            // Rewrite redirect Location headers so the browser
            // follows redirects back through the /api proxy
            // instead of hitting the internal Docker hostname directly.
            const loc = proxyRes.headers['location']
            if (loc) {
              if (loc.startsWith(apiTarget)) {
                proxyRes.headers['location'] = '/api' + loc.slice(apiTarget.length)
              } else if (loc.startsWith('/')) {
                proxyRes.headers['location'] = '/api' + loc
              }
            }
          })
        },
      },
    },
  },
})
