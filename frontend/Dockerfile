### Stage 1 – Build with UI5 Tooling ###
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --ignore-scripts

COPY ui5.yaml ./
COPY webapp/ ./webapp/

RUN npx ui5 build --all --clean-dest --dest dist

### Stage 2 – Serve with Nginx ###
FROM nginx:1.27-alpine

# Remove default nginx site
RUN rm -rf /usr/share/nginx/html/*

# Custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built webapp artefacts (index.html + Component-preload, minified JS/CSS, i18n, etc.)
COPY --from=builder /app/dist /usr/share/nginx/html

# Entrypoint to inject env vars at runtime
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Nginx runs on port 80
EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
