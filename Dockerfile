FROM python:3.13.3-alpine3.21@sha256:452682e4648deafe431ad2f2391d726d7c52f0ff291be8bd4074b10379bb89ff
RUN adduser --disabled-password cover-letter-writer \
    && apk --no-cache add uv
USER cover-letter-writer
WORKDIR /opt/cover-letter-writer
COPY pyproject.toml web.py /opt/cover-letter-writer/
ENTRYPOINT [ "uv", "run", "web.py" ]
