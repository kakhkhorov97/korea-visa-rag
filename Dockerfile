FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000

# Build the index at startup (needs data in data/raw), then serve the web app + API.
#   docker build -t korea-visa-rag .
#   docker run -p 8000:8000 --env-file .env korea-visa-rag
CMD ["sh", "-c", "python scripts/build_index.py && uvicorn visarag.api:app --app-dir src --host 0.0.0.0 --port 8000"]
