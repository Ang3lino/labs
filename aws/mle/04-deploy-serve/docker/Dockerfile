FROM python:3.11-slim

RUN pip install --no-cache-dir torch fastapi uvicorn

WORKDIR /app
COPY serve.py /app/serve.py

EXPOSE 8080

CMD ["uvicorn", "serve:app", "--host", "0.0.0.0", "--port", "8080"]
