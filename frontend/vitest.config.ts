import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.ts'],
    globals: false,
    restoreMocks: true,
    // Ambiente com outros processos concorrentes (pytest/build) pode elevar o
    // tempo de alguns testes acima dos 5s padrão; 30s mantém a suíte estável
    // sem esconder travamentos reais (um teste realmente preso ainda falha).
    testTimeout: 30000,
    hookTimeout: 30000,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary', 'html'],
      reportOnFailure: true,
      reportsDirectory: 'coverage',
      include: ['src/lib/**/*.ts', 'src/api/**/*.ts', 'src/components/**/*.vue'],
      exclude: ['src/**/*.test.ts', 'src/test/**'],
    },
  },
})
