FROM node:22-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
# Vite inlines this at BUILD time. It is not a runtime variable: changing it
# means rebuilding the image, not restarting the container.
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:1.27-alpine
RUN apk add --no-cache openssl
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY docker-entrypoint.d/10-tls-bootstrap.sh /docker-entrypoint.d/10-tls-bootstrap.sh
RUN chmod +x /docker-entrypoint.d/10-tls-bootstrap.sh
COPY --from=build /app/dist /usr/share/nginx/html
# Substitute DOMAIN only — nginx's own $host / $uri / $scheme must survive.
ENV NGINX_ENVSUBST_FILTER=^DOMAIN
EXPOSE 80 443
