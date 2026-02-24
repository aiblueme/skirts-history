# ============================================================
# Stage 1 — Build
# ============================================================
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (layer cache)
COPY package*.json ./
RUN npm ci --prefer-offline

# Copy source (node_modules excluded via .dockerignore)
COPY astro.config.mjs tsconfig.json ./
COPY src/ src/
COPY public/ public/
COPY research.json ./

# Build static site into dist/
RUN npm run build

# ============================================================
# Stage 2 — Serve
# ============================================================
FROM nginx:1.27-alpine AS production

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf 2>/dev/null; true

# Copy built static files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy scraped image assets (not processed by Astro, served directly)
COPY assets/ /usr/share/nginx/html/assets/

# Custom nginx config
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
