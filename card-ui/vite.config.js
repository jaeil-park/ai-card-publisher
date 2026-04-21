import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: './',   // Playwright가 file:// 로 열 수 있도록 상대경로 빌드
  build: {
    outDir: '../card-ui-dist',
    emptyOutDir: true,
  },
})
