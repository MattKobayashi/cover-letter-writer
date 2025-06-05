FROM python:3.13.3-alpine3.22@sha256:a94caf6aab428e086bc398beaf64a6b7a0fad4589573462f52362fd760e64cc9
RUN adduser --disabled-password cover-letter-writer \
    && apk --no-cache add curl uv
USER cover-letter-writer
WORKDIR /opt/cover-letter-writer
COPY pyproject.toml web.py /opt/cover-letter-writer/
ENTRYPOINT [ "uv", "run", "web.py" ]
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -fsSL http://127.0.0.1:8000/health | grep 'ok'
