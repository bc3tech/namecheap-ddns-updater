FROM python:3.14-slim

WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.org/simple/

COPY requirements.txt .
RUN pip install --no-cache-dir --index-url "$PIP_INDEX_URL" -r requirements.txt

COPY app.py .

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
