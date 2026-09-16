# 🏭 Article Foundry

### 🔒 Your own local idea foundry → papers, patents, and science communication

> **Yes, there is a lot of noise about piracy, privacy, and whether somebody might steal your ideas. Well, now you can run your own model and do your idea generation locally. I write papers, patents, and some science and technology communication, and now you can do all of that locally. Here is the repository: clone it, connect your own resources, and build your own document foundry!**

**Article Foundry** is a *local-first* system for turning notes, fragments, ideas, and sources accumulated over time into a structured knowledge base and, whenever you are ready, compiling that knowledge into a **science/technology communication article**, an **IEEE-style scientific paper**, or a **patent draft**.

The idea is simple: instead of starting every document from a blank page, you continuously feed your own knowledge foundry. Article Foundry connects concepts, keeps track of sources, and uses **your own LLM endpoint** to help organize and synthesize the material.

👨‍💻 Created by **Prof. Alberto Muñoz — Tecnológico de Monterrey**

> 🚫 **There is intentionally no link to a hosted Article Foundry instance in this README.** This repository is meant to be cloned and run with **your own compute, your own LLM, your own storage, and your own infrastructure**. Please do not use the author's private server as a public backend.

---

## ✨ What does it do?

```text
💡 Fragments and ideas
        ↓
🔑 Keywords + concepts
        ↓
🧠 Taxonomy / semantic graph
        ↓
📚 Sources and evidence
        ↓
🏭 Article Foundry
        ↓
   ┌────────────────┬──────────────┬──────────────┐
   │ 📰 Communication│ 📄 IEEE Paper│ 💡 Patent    │
   └────────────────┴──────────────┴──────────────┘
        ↓
🧾 LaTeX → 📕 PDF
```

You can add text incrementally and in different languages. The system keeps persistent project memory and organizes knowledge approximately as:

```text
fragment → concepts → subtopics → topics
         → semantic relations → evidence → sources
         → claims → contradictions → knowledge gaps
```

## 🚀 Main features

- 🧠 **Local LLM support** through an OpenAI-compatible endpoint.
- 🔒 **Local-first:** fragments, projects, and generated artifacts can stay on your own machine.
- 🧩 Incremental ingestion of ideas and text fragments.
- 🔑 LLM-assisted keyword and concept extraction.
- 🕸️ Taxonomy and semantic relationships between fragments.
- 🌍 Multilingual input and document generation.
- 📚 Sources in BibTeX, DOI, URL, or free-form citation format.
- 📰 Compiler for **science/technology communication**.
- 📄 Compiler for **scientific / IEEE-style papers**.
- 💡 Compiler for **patent drafts**.
- 🧾 Automatic **LaTeX** generation.
- 📕 **PDF** compilation and in-browser preview.
- 💾 Persistent SQLite knowledge base.
- ☁️ Optional Google Drive synchronization through `rclone`.
- 🐧 Can run as an isolated `systemd` service.
- 🌐 Can optionally sit behind your own reverse proxy or tunnel.

> ⚠️ Article Foundry assists with organization and drafting. For scientific papers, verify results, claims, and references before publication. For patents, independently review claims, inventorship, novelty, and jurisdiction-specific requirements and seek professional advice when appropriate.

---

## 🧱 Architecture

```text
Your browser
     │
     ▼
Article Foundry / FastAPI
     ├── SQLite knowledge base
     ├── Your local LLM adapter
     ├── Semantic analysis
     ├── Editorial compilers
     └── LaTeX compiler
              │
              ▼
          TEX + PDF
```

The LLM itself is **not included** in this repository. Article Foundry consumes an OpenAI-compatible endpoint, allowing you to connect the local inference server and model that make sense for your hardware.

**Nothing in the public repository requires or should point to the author's running LLM server.** Configure your own endpoint before using the application.

---

## 📦 Clone it

```bash
git clone https://github.com/LuisAlbertoMunozUbando/Article-Foundry.git
cd Article-Foundry
```

## ⚙️ Quick installation

You need Python 3 and an OpenAI-compatible LLM server that **you control**.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and point Article Foundry to **your own local inference server**. Never commit real credentials to Git.

Example configuration:

```dotenv
ARTICLE_FOUNDRY_DB=./data/article_foundry.db
ARTICLE_FOUNDRY_ARTIFACTS=./data/artifacts
ARTICLE_FOUNDRY_LLM_BASE_URL=http://127.0.0.1:8001/v1
ARTICLE_FOUNDRY_LLM_API_KEY=local
ARTICLE_FOUNDRY_LLM_MODEL=your-local-model
ARTICLE_FOUNDRY_PORT=8040
```

`127.0.0.1:8001` above is only an **example localhost address**. It refers to port 8001 on the machine where *you* run Article Foundry; it does not connect to the author's infrastructure.

Start Article Foundry:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8040
```

Then access it through localhost, SSH port forwarding, or a reverse proxy/tunnel that **you configure on your own infrastructure**.

---

## 🧪 Workflow

### 1. 💡 Create a project

Each project keeps its own fragments, concepts, relationships, sources, and generated documents.

### 2. ✍️ Feed the foundry

Paste an idea, paragraph, result, reflection, or fragment. Keep adding material over days or weeks; you do not need to write the complete document at once.

### 3. 📚 Add sources

Keep bibliography and evidence together with the knowledge you are building.

### 4. 🧠 Let the knowledge map grow

Article Foundry extracts concepts and builds relationships across the accumulated material.

### 5. 🏭 Compile

Choose an editorial output:

- 📰 **Communication:** Context → Problem → Analogy → Explanation → Evidence → Implications → Closing.
- 📄 **IEEE:** Title → Abstract → Keywords → Introduction → Related Work → Methodology → Experiments → Results → Discussion → Conclusion → References.
- 💡 **Patent:** Title → Technical Field → Background → Problem → Summary → Detailed Description → Embodiments → Figures → Claims → Abstract.

The result is saved as **LaTeX** and, when a compatible TeX compiler is available on your system, as a **PDF**.

---

## 🌍 Languages

The interface and workflow support multiple languages, including:

🇲🇽 Español · 🇬🇧 English · 🇫🇷 Français · 🇮🇹 Italiano · 🇩🇪 Deutsch · 🇯🇵 日本語 · 🇨🇳 中文 · 🇮🇱 עברית · 🇦🇪 العربية · 🇷🇺 Русский · 🇰🇷 한국어

The input language can be different from the final document language.

---

## ☁️ Optional Google Drive backup

The repository includes `deploy/drive_sync.py` to create a local snapshot of the database and export projects/artifacts before synchronizing them with `rclone`.

This integration is **optional** and must be configured with **your own Google Drive account, your own rclone remote, and your own destination folder**.

Do **not** copy the author's Google Drive folder IDs or OAuth configuration. Do **not** commit OAuth tokens, passwords, private `.env` files, rclone configuration files, Cloudflare credentials, or other secrets.

---

## 🔐 Privacy and security

The purpose of Article Foundry is to let you run the document-generation pipeline on infrastructure you control.

For a genuinely local workflow:

- run the LLM on your own hardware;
- point `ARTICLE_FOUNDRY_LLM_BASE_URL` to your own local inference endpoint;
- keep the SQLite database and artifacts on storage you control;
- use external synchronization only if you explicitly want it;
- do not expose the application publicly unless you add appropriate authentication and HTTPS.

The public repository contains **no passwords, OAuth tokens, private server credentials, Cloudflare tunnel tokens, or Google Drive credentials**.

---

## 🧩 Designed to coexist with your infrastructure

Article Foundry is designed as an independent service. It does not need to stop, restart, or reconfigure your other AI services. If you already have a compatible local LLM server, Article Foundry simply consumes its HTTP API.

You are encouraged to adapt the ports, models, storage, deployment, and backup strategy to your own machine.

---

## 🛠️ Main API

```text
GET    /api/projects
POST   /api/projects
GET    /api/projects/{id}
POST   /api/projects/{id}/fragments
POST   /api/projects/{id}/sources
POST   /api/projects/{id}/compile
GET    /api/projects/{id}/artifacts/{filename}
GET    /api/system/llm
```

---

## 🤝 Build your own Foundry

Clone the repository, connect **your own local model**, adapt the editorial workflow, and turn it into your own research and writing memory.

```bash
git clone https://github.com/LuisAlbertoMunozUbando/Article-Foundry.git
```

No hosted account is required. No author's server is required. **The intended deployment is yours.**

**💡 Your ideas. 🧠 Your model. 💻 Your machine. 🏭 Your Foundry.**

---

Made with 🤖 + 🧠 + ☕ by **Alberto Muñoz**.
