FROM python:3.11-slim
WORKDIR /app
COPY ingestion/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY ingestion/app.py /app/app.py
COPY sample-data /app/sample-data
EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
