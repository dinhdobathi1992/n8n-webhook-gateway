FROM node:20-slim AS ui-builder
WORKDIR /ui
COPY ui/package.json ./
RUN npm install
COPY ui/ .
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/
COPY --from=ui-builder /ui/dist ui/dist/
EXPOSE 3000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
