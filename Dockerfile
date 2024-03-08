FROM python:3.12.1-slim

WORKDIR /app

COPY poetry.lock pyproject.toml ./

ENV PYTHONPATH=${PYTHONPATH}:${PWD}
RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev

RUN apt update && apt install ffmpeg -y

COPY muxer /app/muxer
COPY README.md /app

RUN mkdir input
RUN mkdir output

CMD ["poetry", "run", "python", "-m", "muxer"]
