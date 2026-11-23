# Christian Pure Bible Search: one small image for Docker Hub, Hugging Face Spaces, Umbrel, CasaOS and Unraid.
FROM python:3.13-slim

LABEL org.opencontainers.image.title="Christian Pure Bible Search" \
      org.opencontainers.image.description="Search the Bible and Christian Pure's prayers on your own computer. Works offline." \
      org.opencontainers.image.url="https://christianpure.com/?utm_source=docker&utm_medium=app&utm_campaign=bible-search-app" \
      org.opencontainers.image.source="https://github.com/christianpure/bible-search" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="Christian Pure"

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 PORT=8417 DATA_DIR=/data STUDY_SOURCE=docker

RUN useradd --uid 1000 --create-home study && mkdir -p /data && chown study /data
WORKDIR /app
COPY --chown=study . /app
USER study
# Build the index once so the first start is instant and works with no network.
RUN DATA_DIR=/app/data/local STUDY_OFFLINE=1 python app.py --prepare && rm -rf /app/data/local

EXPOSE 8417
VOLUME /data
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import urllib.request,os;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8417')+'/healthz',timeout=4)"
CMD ["python", "app.py"]
