FROM node:22-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:1.30-alpine
# 1.28.3-r1 / curl 8.17.0-r1 은 Critical. 1.30 이 nginx 패치를 포함하고, apk 가 Alpine curl·openssl 을 맞춘다.
RUN apk upgrade --no-cache curl libcurl openssl libssl3 libcrypto3
ENV BACKEND_UPSTREAM=backend:8000
ENV NGINX_ENVSUBST_FILTER=BACKEND_UPSTREAM
COPY docker/nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
