FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock

COPY app ./app
COPY scripts ./scripts

RUN groupadd --gid 1000 money-note \
    && useradd --uid 1000 --gid 1000 --no-create-home money-note \
    && mkdir -p /app/data /app/downloads \
    && chown -R money-note:money-note /app

USER money-note

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
