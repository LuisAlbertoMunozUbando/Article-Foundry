# Article Foundry

Incremental knowledge-to-document system for **Divulgacion**, **IEEE paper**, and **Patent** workflows.

## Safety boundary
Article Foundry is a new, isolated service. It does **not modify, restart, stop, or reconfigure** any existing YouTubeKnowledge, SlideExtractor, Research Knowledge, STL, or Innovaction service. Existing local LLMs are consumed only through configurable HTTP endpoints.

## Architecture

Browser -> Article Foundry API -> SQLite knowledge graph / local LLM adapter / LaTeX compiler -> PDF

Default LLM adapter: OpenAI-compatible endpoint at `http://127.0.0.1:8001/v1` (override in `.env`).

## Quick start on DGX Spark

```bash
cd ~/Article-Foundry
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8030
```

Open `http://127.0.0.1:8030`.

For a LAN test only, use `--host 0.0.0.0`. For production, keep it on localhost and put a new reverse proxy/tunnel in front of port 8030; do not reuse or edit existing service units.

## Features
- Projects and incremental fragments
- LLM-assisted keyword extraction and semantic taxonomy
- Relationship detection between fragments
- Persistent SQLite graph
- Three editorial compilers: divulgacion, IEEE, patent
- LaTeX source generation
- Immediate PDF compilation when `latexmk` or `pdflatex` is installed
- PDF embedded in the web UI
- `.tex` and `.pdf` downloads
- LLM endpoint/model discovery via `/api/system/llm`

## API
- `POST /api/projects`
- `GET /api/projects/{id}`
- `POST /api/projects/{id}/fragments`
- `POST /api/projects/{id}/compile`
- `GET /api/projects/{id}/artifacts/{filename}`
- `GET /api/system/llm`

## Existing Spark services
They remain external dependencies only. Article Foundry never invokes `systemctl`, Docker lifecycle commands, or writes into their directories.
