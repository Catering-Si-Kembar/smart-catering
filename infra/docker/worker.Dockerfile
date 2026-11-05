FROM node:24.15.0-alpine3.23@sha256:d1b3b4da11eefd5941e7f0b9cf17783fc99d9c6fc34884a665f40a06dbdfc94f AS deps
WORKDIR /app

COPY package.json package-lock.json .npmrc ./
COPY apps/ai-service/package.json ./apps/ai-service/package.json
COPY apps/api/package.json ./apps/api/package.json
COPY apps/web/package.json ./apps/web/package.json
COPY apps/worker/package.json ./apps/worker/package.json
COPY packages/db/package.json ./packages/db/package.json
COPY packages/types/package.json ./packages/types/package.json

RUN npm install --global npm@12.1.0 && npm ci

FROM deps AS build
WORKDIR /app

COPY tsconfig.base.json ./
COPY packages/types ./packages/types
COPY apps/worker ./apps/worker

RUN npm run build --workspace=@smart-catering/types \
  && npm run build --workspace=@smart-catering/worker

FROM node:24.15.0-alpine3.23@sha256:d1b3b4da11eefd5941e7f0b9cf17783fc99d9c6fc34884a665f40a06dbdfc94f AS runtime
WORKDIR /app

ENV NODE_ENV=production
ENV WORKER_HOST=0.0.0.0
ENV WORKER_PORT=3002

COPY --chown=node:node --from=build /app/apps/worker/package.json ./apps/worker/package.json
COPY --chown=node:node --from=build /app/apps/worker/dist ./apps/worker/dist

USER node
EXPOSE 3002

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:3002/health').then((r)=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]

CMD ["node", "apps/worker/dist/index.js"]
