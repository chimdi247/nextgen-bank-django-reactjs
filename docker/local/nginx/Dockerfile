# syntax=docker/dockerfile:1

# ---- stage 1: build the React app (frontend/)
FROM docker.io/node:22-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json ./
RUN --mount=type=cache,target=/root/.npm npm install --no-audit --no-fund
COPY frontend/ ./
# links shown on the admin "System" page (public URLs, baked into the bundle)
ARG VITE_GRAFANA_URL=http://34.171.152.81:3001
ARG VITE_MAILPIT_URL=http://34.171.152.81:8025
ARG VITE_RABBITMQ_URL=http://34.171.152.81:15672
ARG VITE_FLOWER_URL=http://34.171.152.81:5555
ARG VITE_REDIS_UI_URL=http://34.171.152.81:5540
ENV VITE_GRAFANA_URL=$VITE_GRAFANA_URL VITE_MAILPIT_URL=$VITE_MAILPIT_URL VITE_RABBITMQ_URL=$VITE_RABBITMQ_URL \
    VITE_FLOWER_URL=$VITE_FLOWER_URL VITE_REDIS_UI_URL=$VITE_REDIS_UI_URL
RUN npm run build

# ---- stage 2: nginx = static SPA + reverse proxy to Django
FROM docker.io/nginx:1.27.0-alpine3.19-slim
RUN rm /etc/nginx/conf.d/default.conf
COPY docker/local/nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend-build /frontend/dist /usr/share/nginx/html
