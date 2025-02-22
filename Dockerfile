FROM python:3.13.2-slim

RUN apt update && apt install ffmpeg -y

# Configure Poetry
ENV POETRY_VERSION=1.8.2
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv
ENV POETRY_CACHE_DIR=/opt/.cache

# Install poetry separated from system interpreter
RUN python3 -m venv $POETRY_VENV \
	&& $POETRY_VENV/bin/pip install -U pip setuptools \
	&& $POETRY_VENV/bin/pip install poetry==${POETRY_VERSION}

# Add `poetry` to PATH
ENV PATH="${PATH}:${POETRY_VENV}/bin"

WORKDIR /app

COPY poetry.lock pyproject.toml ./
COPY README.md /app

RUN poetry install --without dev --no-interaction --no-ansi

COPY muxer /app/muxer
RUN mkdir input
RUN mkdir output

CMD poetry run luigid \
    & poetry run python -m muxer
