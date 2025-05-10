FROM python:3.13.3-alpine3.21@sha256:f80206d96683c1b27cd522dc300f791a48362b895ad5c0bdd26f78f853c76fa5
RUN adduser --disabled-password cover-letter-writer \
    && apk --no-cache add uv
USER cover-letter-writer
WORKDIR /opt/cover-letter-writer
COPY pyproject.toml web.py /opt/cover-letter-writer/
ENTRYPOINT [ "uv", "run", "web.py" ]
