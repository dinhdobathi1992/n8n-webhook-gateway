FROM node:22-slim AS ui-builder
WORKDIR /ui
COPY zscaler.pem /tmp/zscaler.pem
ENV NODE_EXTRA_CA_CERTS=/tmp/zscaler.pem
COPY ui/package.json ./
RUN npm install
COPY ui/ .
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY zscaler.pem /usr/local/share/ca-certificates/zscaler.crt
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && update-ca-certificates && rm -rf /var/lib/apt/lists/*
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/
COPY scripts/ scripts/
COPY --from=ui-builder /ui/dist ui/dist/
EXPOSE 3000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
