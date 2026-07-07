FROM python:3.11-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY contents ./contents

ENV PYTHONUNBUFFERED=1

# 첫 기동 시 테이블 생성/시드 후 API 서버 시작
CMD ["sh", "-c", "python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
