import { defineConfig } from 'vite'

// base: './' maakt relatieve paden in de build.
// Daardoor werkt de site ook in een submap, zoals op GitHub Pages.
export default defineConfig({
  base: './',
  build: { outDir: 'dist' }
})
