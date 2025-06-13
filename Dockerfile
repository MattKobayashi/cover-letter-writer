FROM python:3.13.5-alpine3.22@sha256:d49ec50fe9db96f85a908bac1d9e23cba93211a5721ae93b64ab1849f2370397
RUN adduser --disabled-password cover-letter-writer \
    && apk --no-cache add curl uv
USER cover-letter-writer
WORKDIR /opt/cover-letter-writer
COPY pyproject.toml web.py /opt/cover-letter-writer/
ENTRYPOINT [ "uv", "run", "web.py" ]
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsSL http://127.0.0.1:8000/health | grep 'ok'
