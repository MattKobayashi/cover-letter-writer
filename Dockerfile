FROM python:3.13.4-alpine3.22@sha256:b4d299311845147e7e47c970566906caf8378a1f04e5d3de65b5f2e834f8e3bf
RUN adduser --disabled-password cover-letter-writer \
    && apk --no-cache add curl uv
USER cover-letter-writer
WORKDIR /opt/cover-letter-writer
COPY pyproject.toml web.py /opt/cover-letter-writer/
ENTRYPOINT [ "uv", "run", "web.py" ]
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -fsSL http://127.0.0.1:8000/health | grep 'ok'
