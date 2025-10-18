FROM python:3.11-slim

ENV POETRY_VIRTUALENVS_CREATE=false \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir poetry==1.8.3
COPY pyproject.toml poetry.lock README.md /app/
WORKDIR /app
RUN poetry install --only main --no-root
COPY src /app/src
COPY scripts /app/scripts

EXPOSE 8000
CMD ["poetry", "run", "uvicorn", "genesis.api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
