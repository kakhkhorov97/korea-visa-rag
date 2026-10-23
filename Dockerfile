FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/src \
    VISARAG_DATA_DIR=/var/lib/visarag VISARAG_RAW_DIR=/app/data/public_raw
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home app && mkdir -p /var/lib/visarag \
    && chown app:app /var/lib/visarag
COPY src/ src/
COPY web/ web/
COPY scripts/build_index.py scripts/serve.py scripts/
COPY data/public_raw/ data/public_raw/
USER app
EXPOSE 8000
CMD ["python", "scripts/serve.py"]
