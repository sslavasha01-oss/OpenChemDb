FROM node:lts-alpine as build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# 2. Этап "доставки"
FROM alpine:latest
# Мы просто кладем билд в папку, которую потом заберет Caddy
COPY --from=build-stage /app/dist /dist
CMD ["sh", "-c", "cp -R /dist/* /output/"]