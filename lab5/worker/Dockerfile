FROM python:3.13-alpine

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN adduser -D -u 1000 worker
USER 1000

ENTRYPOINT [ "python", "main.py" ]