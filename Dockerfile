FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir flask openpyxl gunicorn

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"]