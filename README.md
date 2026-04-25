# Rechnungserkennung

Selbst-gehostetes MVP zur Rechnungserkennung mit PostgreSQL, MinIO und Docling.

## Aktueller Fokus

Wochen 1–2:

- Git-Repo sauber aufsetzen
- Docker Compose mit PostgreSQL + MinIO
- Docling auf 5 Test-Rechnungen laufen lassen
- Lücken dokumentieren

## Docker-Infrastruktur

Die Projekt-Compose startet PostgreSQL und MinIO lokal auf dem Server. Persistente Daten liegen passend zur Server-Struktur unter `/srv/data/rechnungserkennung/`.

```bash
docker compose up -d
docker compose ps
```

Lokale Endpunkte:

- PostgreSQL: `127.0.0.1:55432`
- MinIO API: `127.0.0.1:9000`
- MinIO Console: `127.0.0.1:9001`

Beim Start legt `minio-init` die Buckets aus `.env` an: `invoices` und `docling-output`.

## Docling

Docling ist lokal in einer Projekt-`.venv` installiert.

```bash
source .venv/bin/activate
docling --version
```

Installationsbasis im Repo:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Grundregel

Keine echten Mandanten-/Kundendaten ins Git.
Keine Secrets ins Git.
Keine Cloud-KI für echte Rechnungsdaten.
