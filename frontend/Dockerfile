FROM node:20-slim AS build

WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .

# The production build (served statically, no dev-server proxy) needs
# the backend's URL baked in at build time — Vite replaces
# import.meta.env.VITE_API_BASE_URL with this literal value in the
# built bundle. Defaults to the backend's host-mapped port from
# docker-compose.yml; override with --build-arg if the backend is
# reachable at a different address (e.g. deploying somewhere the
# presenter's browser can't reach "localhost" directly).
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM node:20-slim
WORKDIR /app
RUN npm install -g serve
COPY --from=build /app/dist ./dist

EXPOSE 5173
CMD ["serve", "-s", "dist", "-l", "5173"]
