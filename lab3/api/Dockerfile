FROM python:3.13-alpine

WORKDIR /app

COPY requirements.txt ./

RUN apk add --no-cache curl

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT [ "python", "main.py" ]

RUN adduser -D -u 1000 app

ENV HEALTH_FAIL=true
USER 1000

EXPOSE 8000




