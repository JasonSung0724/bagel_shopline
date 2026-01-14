# Stage 1: Builder
FROM node:20-alpine AS builder
WORKDIR /app

# Copy package files and install ALL dependencies (including devDependencies for build)
COPY package.json package-lock.json* ./
RUN npm ci --legacy-peer-deps

# Copy source and build
COPY . .

# 清理快取並重新構建
RUN rm -rf .next .turbo

# 設置環境變數避免快取問題
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

RUN npm run build

# Stage 2: Runner
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV TZ=Asia/Taipei

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
