FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV HOST=0.0.0.0 PORT=8000 BRITSMAID_ENV=production BRITSMAID_DATA_DIR=/data
EXPOSE 8000
CMD ["python", "app.py"]
