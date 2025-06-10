
# Phase 1 - about 350MB
FROM python:3.10.18-alpine3.22 AS builder

WORKDIR /app

COPY pyproject.toml README.rst LICENSE ./
COPY weasyprint/ ./weasyprint/

RUN pip install --upgrade pip
RUN pip install build
RUN python -m build --wheel
#RUN pip install dist/*.whl

# Phase 2 - about 308MB
FROM python:3.10.18-alpine3.22

RUN apk add --no-cache py3-pip so:libgobject-2.0.so.0 so:libpango-1.0.so.0 so:libharfbuzz.so.0 so:libharfbuzz-subset.so.0 so:libfontconfig.so.1 so:libpangoft2-1.0.so.0
RUN apk add --no-cache font-liberation font-liberation-sans-narrow ttf-linux-libertine

WORKDIR /app/dist

COPY --from=builder /app/dist/*.whl .

RUN pip install --no-cache-dir *.whl

VOLUME /data
WORKDIR /data

ENTRYPOINT ["python", "-m", "weasyprint"]