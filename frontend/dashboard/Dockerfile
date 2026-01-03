FROM node:22-alpine AS builder

WORKDIR /app

COPY frontend/dashboard/package*.json ./

RUN npm install

COPY frontend/dashboard .

RUN npm run build

FROM nginx:alpine AS final

COPY frontend/dashboard/nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=builder /app/build /usr/share/nginx/html

ENTRYPOINT ["nginx", "-g", "daemon off;"]
