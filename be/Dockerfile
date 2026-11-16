FROM python:3.12-slim
WORKDIR /srv
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -m app && mkdir -p /data/uploads && chown -R app /data /srv
USER app
EXPOSE 8000
# 4 worker ~ dư cho 250 user; migration chạy riêng (xem docker-compose: service migrate)
CMD ["gunicorn","app.main:app","-k","uvicorn.workers.UvicornWorker","-w","4","-b","0.0.0.0:8000","--timeout","60"]
