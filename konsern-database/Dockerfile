# HR Analyse — Docker image
# Lokal webapplikasjon for HR-analyse med FastAPI + Chart.js

FROM python:3.13-slim

# Systemavhengigheter for matplotlib
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libfreetype6 \
        libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installer Python-avhengigheter først (cache-vennlig)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-bygg matplotlib font cache (unngår treg første kjøring)
RUN python -c "import matplotlib.pyplot"

# Kopier applikasjonskode
COPY hr_database/ hr_database/
COPY web/ web/
COPY hr_cli.py .

# Opprett data-mappe for SQLite-persistens
RUN mkdir -p /app/data

# Miljøvariabler
ENV DB_PATH=/app/data/ansatte.db
ENV HOST=0.0.0.0
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

# Kjør webapplikasjonen
CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8080"]
