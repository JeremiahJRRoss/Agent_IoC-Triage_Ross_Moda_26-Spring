FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    IOC_TRIAGE_NO_PROMPT=1

WORKDIR /app

# Non-root runtime user (UID 10001, no shell, no home).
RUN useradd --uid 10001 --system --no-create-home --shell /usr/sbin/nologin appuser

COPY requirements.lock .
RUN pip install -r requirements.lock

COPY agent/ ./agent/
COPY web/ ./web/
COPY fixtures/ ./fixtures/
COPY ioc_triage_agent.py .

USER appuser

EXPOSE 7777

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7777/health').read()" || exit 1

CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "7777"]
