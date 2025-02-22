FROM python:3.13.2-slim

WORKDIR /app

COPY poetry.lock pyproject.toml ./
COPY README.md /app
COPY muxer /app/muxer

ENV PYTHONPATH=${PYTHONPATH}:${PWD}
RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --without dev

RUN apt update && apt install ffmpeg -y


RUN mkdir input
RUN mkdir output

CMD poetry run luigid \
    & poetry run python -m muxer
