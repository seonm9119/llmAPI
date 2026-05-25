FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install -r /app/requirements.txt

COPY app.py config.py client.py /app/
COPY routes/ /app/routes/

EXPOSE 8003

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8003"]
