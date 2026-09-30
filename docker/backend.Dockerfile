FROM python:3.11-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY contents ./contents

ENV PYTHONUNBUFFERED=1
# 영구 미디어 저장소 — 파드에서 /app/media 에 S3 가 마운트된다. 에디터 이미지(authored/)와
# 인제스트 썸네일(thumbnails/)은 전부 이 아래에 쓰여 재기동 후에도 남는다. 파드는 .env 를
# 읽지 않고 ExternalSecret 은 매핑된 키만 주입하므로 이미지 안에서 명시적으로 고정한다.
ENV MEDIA_DIR=/app/media
# 마운트가 빠진 채 기동하면 휘발성 디렉터리에 쓰다 재기동 때 또 잃는다 — 기동 자체를 거부한다
ENV MEDIA_REQUIRE_MOUNT=true

# 첫 기동 시 테이블 생성/시드 후 API 서버 시작
CMD ["sh", "-c", "python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
