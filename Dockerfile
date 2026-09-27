FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
WORKDIR /app
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
RUN useradd --create-home swm && mkdir -p /app/data && chown swm:swm /app/data
COPY backend/ backend/
COPY migrations/ migrations/
COPY alembic.ini ./
COPY --from=web /web/dist frontend/dist/
USER swm
EXPOSE 8000
CMD ["sh", "-c", "python -m alembic upgrade head && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
