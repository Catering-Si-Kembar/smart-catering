FROM python:3.12.16-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=/usr/local/bin/python3.12

WORKDIR /app/apps/ai-service

RUN groupadd --system --gid 10001 aiservice \
  && useradd --system --uid 10001 --gid aiservice --create-home --home-dir /home/aiservice aiservice \
  && pip install --no-cache-dir uv==0.13.7

COPY apps/ai-service/pyproject.toml apps/ai-service/uv.lock apps/ai-service/.python-version ./
COPY apps/ai-service/app ./app

RUN uv sync --frozen --no-dev \
  && chown -R aiservice:aiservice /app /home/aiservice

ENV PATH="/app/apps/ai-service/.venv/bin:${PATH}" \
    APP_ENV=production \
    DOCS_ENABLED=false

USER aiservice
EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.request; r = urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=4); sys.exit(0 if r.status == 200 else 1)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--no-access-log"]
