FROM python:3.14-slim

ARG PORT=80

WORKDIR /app

ENV PIP_INDEX_URL=https://packagefeedproxy.microsoft.io/pypi/simple
ENV UV_INDEX_URL=https://packagefeedproxy.microsoft.io/pypi/simple
ENV PYTHONUNBUFFERED=1
ENV PORT=${PORT}

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE ${PORT}

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --access-logfile - --error-logfile - app:app"]
