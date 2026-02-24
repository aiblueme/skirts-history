import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'http://64.235.43.190:8181',
  output: 'static',
  build: {
    assets: '_astro',
  },
  integrations: [
    sitemap(),
  ],
});
