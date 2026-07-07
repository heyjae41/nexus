import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'
import { createRequire } from 'module'

const frontendDir = path.resolve(__dirname, '.')
const repoRoot = path.resolve(__dirname, '../')

// Test files live at ../test/frontend/ (outside frontend/).
// Bare-specifier resolution from that location never reaches
// frontend/node_modules, so we redirect it with a custom plugin.
const frontendRequire = createRequire(path.join(frontendDir, 'package.json'))

function resolveFromFrontend() {
  return {
    name: 'resolve-from-frontend',
    enforce: 'pre',
    resolveId(id, importer) {
      // Skip relative imports, absolute paths, virtual modules, node builtins,
      // and vitest itself (vitest handles its own module internally)
      if (
        id.startsWith('.') ||
        id.startsWith('/') ||
        id.startsWith('\0') ||
        id === 'vitest' ||
        id.startsWith('vitest/') ||
        id.startsWith('node:') ||
        !importer
      ) {
        return null
      }
      // Resolve all bare imports through frontend/node_modules regardless of
      // where the importer lives — this is required because root: repoRoot
      // breaks Vite's default node_modules walk for files inside frontend/src/
      try {
        return frontendRequire.resolve(id)
      } catch {
        return null
      }
    },
  }
}

export default defineConfig({
  plugins: [react(), resolveFromFrontend()],
  server: {
    fs: {
      allow: [frontendDir, repoRoot],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(frontendDir, 'src'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    root: repoRoot,
    include: ['test/frontend/**/*.test.{js,jsx}'],
    // Proxy setup file is inside frontend/ so @testing-library/jest-dom resolves correctly
    setupFiles: [path.resolve(frontendDir, 'vitest-setup.js')],
  },
})
