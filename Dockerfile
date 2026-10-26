FROM node:24.19.0-bookworm-slim AS web
WORKDIR /build/web
RUN npm install --global pnpm@11.22.0
COPY web/package.json web/pnpm-lock.yaml web/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY web/ ./
RUN pnpm build

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.8.22
WORKDIR /app
COPY engine/ engine/
RUN UV_PROJECT_ENVIRONMENT=../.venv uv sync --project engine --extra local --extra service --extra report --no-dev --frozen
COPY api/ api/
COPY worker/ worker/
COPY mcp/ mcp/
COPY scripts/ scripts/
COPY eval/ eval/
COPY bench/ bench/
COPY docs/ docs/
COPY --from=web /build/web/dist/ web/dist/
RUN useradd --uid 10001 --create-home resonance && mkdir -p outputs && chown -R resonance:resonance /app
USER resonance
ENV RESONANCE_HOST=0.0.0.0 MPLCONFIGDIR=/app/outputs/matplotlib
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=120s CMD [".venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"]
CMD ["sh", "-c", ".venv/bin/python -m scripts.seed_demo && exec .venv/bin/python -m scripts.run_local"]
