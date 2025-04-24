FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

LABEL org.opencontainers.image.source="https://github.com/mizzoudbl/tbep"

CMD [ "python", "app.py" ]