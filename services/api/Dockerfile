FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN groupadd --system app && useradd --system --gid app --create-home app
WORKDIR /app
COPY services/api/requirements.lock ./
RUN pip install --requirement requirements.lock
COPY services/api/app ./app
COPY config ./config
COPY evidence ./evidence
RUN mkdir -p /data/evidence && chown -R app:app /app /data
USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3)"
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--proxy-headers"]
