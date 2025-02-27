FROM python:3.13.2-alpine3.21

USER app
WORKDIR /opt/cover-letter-writer

COPY generate.py pyproject.toml web.py /opt/cover-letter-writer/
RUN apk --update-cache add py3-uv
ENTRYPOINT [ "uv", "run", "web.py" ]
