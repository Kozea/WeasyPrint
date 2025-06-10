
# Phase 1 - about 350MB ############################
FROM python:3.10.18-alpine3.22 AS builder

WORKDIR /app

COPY . .

RUN pip install --upgrade pip
RUN pip install build
RUN python -m build --wheel

# Phase 2 - about 244MB ############################
# Using python:3.10.18-alpine3.22 you get about 308MB
# alpine 3.17 ships python 3.10.x
FROM alpine:3.17

RUN apk add --no-cache python3 py3-pip
RUN apk add --no-cache so:libgobject-2.0.so.0 so:libpango-1.0.so.0 so:libharfbuzz.so.0 so:libharfbuzz-subset.so.0 so:libfontconfig.so.1 so:libpangoft2-1.0.so.0
RUN apk add --no-cache font-liberation font-liberation-sans-narrow ttf-linux-libertine

WORKDIR /app/dist

COPY --from=builder /app/dist/*.whl .

RUN pip install --no-cache-dir *.whl

VOLUME /data
WORKDIR /data

ENTRYPOINT ["python", "-m", "weasyprint"]