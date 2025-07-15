FROM python:3.13.5-alpine@sha256:e08874637f2704667426cb3b8d14581b9cb12dd2c237c8419f65446669443921
RUN adduser --disabled-password cover-letter-writer \
    && apk --no-cache add curl uv
USER cover-letter-writer
WORKDIR /opt/cover-letter-writer
COPY pyproject.toml web.py /opt/cover-letter-writer/
ENTRYPOINT [ "uv", "run", "web.py" ]
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsSL http://127.0.0.1:8000/health | grep 'ok'
