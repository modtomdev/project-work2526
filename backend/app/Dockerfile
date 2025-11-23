FROM python:3.12-slim

WORKDIR /app

COPY backend/app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app .

ENTRYPOINT ["python", "main.py"]
