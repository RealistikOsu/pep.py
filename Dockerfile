FROM python:3.12

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# NOTE: These are handled as image resources, and therefore moved into the image.
COPY ./resources/bible.txt /app/resources/bible.txt

ENV DATA_BIBLE_PATH=/app/resources/bible.txt

# Requirements
COPY ./requirements/main.txt /app/requirements.txt
RUN python3.12 -m pip install -r /app/requirements.txt

# Scripts
COPY ./scripts /app/scripts

# Application.
COPY ./peppy /app/peppy

ENTRYPOINT [ "/app/scripts/bootstrap.sh" ]
