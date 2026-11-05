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

COPY tsconfig.base.json turbo.json ./
COPY scripts/service-environment.mjs scripts/run-service.mjs ./scripts/
COPY packages/types ./packages/types
COPY packages/db ./packages/db
COPY apps/api ./apps/api

ENV NEXT_TELEMETRY_DISABLED=1
ENV DATABASE_URL=postgresql://build:build@127.0.0.1:5432/smart_catering_build?schema=public

RUN npm run build --workspace=@smart-catering/types \
  && npm run build --workspace=@smart-catering/db \
  && npm run build --workspace=@smart-catering/api \
  && mkdir -p /app/apps/api/.next/static /app/apps/api/public

FROM node:24.15.0-alpine3.23@sha256:d1b3b4da11eefd5941e7f0b9cf17783fc99d9c6fc34884a665f40a06dbdfc94f AS runtime
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3001
ENV HOSTNAME=0.0.0.0
ENV DOCS_ENABLED=false

COPY --chown=node:node --from=build /app/apps/api/.next/standalone ./
COPY --chown=node:node --from=build /app/apps/api/.next/static ./apps/api/.next/static
COPY --chown=node:node --from=build /app/apps/api/public ./apps/api/public

USER node
EXPOSE 3001

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:3001/health').then((r)=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]

CMD ["node", "apps/api/server.js"]
