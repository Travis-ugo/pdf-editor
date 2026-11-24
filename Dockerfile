# PDF Studio web app, as deployed on Render (see render.yaml).
# LibreOffice is included so Word / Excel / PowerPoint / OpenDocument / RTF uploads can be
# converted to PDF; everything else works without it.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PDF_STUDIO_HOSTED=1 \
    HOME=/tmp

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libreoffice-writer-nogui libreoffice-calc-nogui libreoffice-impress-nogui \
        fonts-dejavu-core fonts-liberation fonts-crosextra-carlito fonts-crosextra-caladea \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY pdf_duplicator ./pdf_duplicator
COPY run.py run_web.py setup.py ./

RUN useradd --create-home --uid 10001 app
USER app

# Render provides $PORT. One worker: uploads are kept on this container's disk and memory is
# tight on small instances; threads let it serve several requests at once.
CMD gunicorn pdf_duplicator.web:app \
    --bind 0.0.0.0:${PORT:-10000} \
    --workers 1 --threads 4 --timeout 180 \
    --access-logfile -
