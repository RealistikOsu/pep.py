FROM python:3.9

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# NOTE: These are handled as image resources, and therefore moved into the image.
COPY ./resources/bible.txt /app/resources/bible.txt

ENV DATA_BIBLE_PATH=/app/resources/bible.txt

# Requirements
COPY ./requirements/main.txt /app/requirements.txt
RUN python3.9 -m pip install -r /app/requirements.txt

# Scripts
COPY ./scripts /app/scripts

# Application.
COPY ./peppy /app/peppy

RUN chmod +x -R /app/scripts

ENTRYPOINT [ "/app/scripts/bootstrap.sh" ]
