FROM python:3.12-slim

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry==2.2.1

# Make Poetry install to the global env instead of creating a venv
RUN poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --no-interaction --no-ansi --only main

COPY . .

EXPOSE 8002

CMD ["sh", "-c", "poetry run uvicorn main:app --host 0.0.0.0 --port 8002"]
