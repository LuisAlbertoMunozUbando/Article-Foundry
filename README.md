# 🏭 Article Foundry

### 🔒 Tu propia fundición local de ideas → papers, patentes y divulgación

> **Pues sí, hay mucho ruido de piratería y de que si se roban tus ideas. Bueno, ahora sí puedes tener tu propio modelo y puedes hacer tu generación de ideas local. Yo escribo papers, patentes y algo de divulgación, y ahora puedes hacer todo en local. ¡Aquí el repo para que lo puedas clonar y hacer tu propio foundry de documentos!**

**Article Foundry** es un sistema *local-first* para convertir notas, fragmentos, ideas y fuentes que vas acumulando en una base de conocimiento estructurada y, cuando estés listo, compilarlas como un **artículo de divulgación**, un **paper científico estilo IEEE** o un **borrador de patente**.

La idea es sencilla: en vez de empezar cada documento desde una página en blanco, vas alimentando tu propia fundición de conocimiento. Article Foundry relaciona conceptos, conserva fuentes y utiliza un LLM local para ayudarte a estructurar el material.

🌐 Demo/instancia del autor: **https://foundry.albertomunoz.ai**  
👨‍💻 Autor: **Prof. Alberto Muñoz — Tec de Monterrey**  
🔗 CV: **https://cv.albertomunoz.ai**

---

## ✨ ¿Qué hace?

```text
💡 Fragmentos e ideas
        ↓
🔑 Keywords + conceptos
        ↓
🧠 Taxonomía / grafo semántico
        ↓
📚 Fuentes y evidencia
        ↓
🏭 Article Foundry
        ↓
   ┌──────────────┬──────────────┬──────────────┐
   │ 📰 Divulgación│ 📄 IEEE Paper│ 💡 Patente   │
   └──────────────┴──────────────┴──────────────┘
        ↓
🧾 LaTeX → 📕 PDF
```

Puedes introducir texto poco a poco y en distintos idiomas. El sistema mantiene una memoria persistente del proyecto y organiza el conocimiento aproximadamente como:

```text
fragment → concepts → subtopics → topics
         → semantic relations → evidence → sources
         → claims → contradictions → knowledge gaps
```

## 🚀 Funciones principales

- 🧠 **LLM local** mediante un endpoint compatible con OpenAI.
- 🔒 **Local-first:** tus fragmentos, proyectos y artefactos pueden permanecer en tu propia máquina.
- 🧩 Ingesta incremental de ideas y fragmentos.
- 🔑 Extracción asistida de keywords y conceptos.
- 🕸️ Taxonomía y relaciones semánticas entre fragmentos.
- 🌍 Entrada y generación multilingüe.
- 📚 Fuentes en BibTeX, DOI, URL o texto libre.
- 📰 Compilador para **divulgación**.
- 📄 Compilador para **paper científico / IEEE**.
- 💡 Compilador para **borrador de patente**.
- 🧾 Generación automática de **LaTeX**.
- 📕 Compilación y visualización de **PDF**.
- 💾 Persistencia mediante SQLite.
- ☁️ Sincronización opcional con Google Drive mediante `rclone`.
- 🐧 Preparado para ejecutarse como servicio `systemd`.
- 🌐 Puede publicarse detrás de un reverse proxy o Cloudflare Tunnel.

> ⚠️ Article Foundry ayuda a organizar y redactar material. En papers, verifica resultados y referencias antes de publicar; en patentes, revisa claims, inventorship y requisitos con asesoría profesional cuando corresponda.

---

## 🧱 Arquitectura

```text
Browser
   │
   ▼
FastAPI / Article Foundry
   ├── SQLite knowledge base
   ├── Local LLM adapter
   ├── Semantic analysis
   ├── Editorial compilers
   └── LaTeX compiler
            │
            ▼
        TEX + PDF
```

El LLM **no está incluido** en este repositorio. Article Foundry consume un endpoint local compatible con la API de OpenAI, por lo que puedes conectarlo al servidor/modelo que prefieras.

---

## 📦 Clonar

```bash
git clone https://github.com/LuisAlbertoMunozUbando/Article-Foundry.git
cd Article-Foundry
```

## ⚙️ Instalación rápida

Requiere Python 3 y un servidor LLM compatible con OpenAI.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edita `.env` para apuntar a **tu** servidor local. El archivo de ejemplo contiene únicamente valores de configuración de muestra; no guardes credenciales reales en Git.

Ejemplo conceptual:

```dotenv
ARTICLE_FOUNDRY_DB=./data/article_foundry.db
ARTICLE_FOUNDRY_ARTIFACTS=./data/artifacts
ARTICLE_FOUNDRY_LLM_BASE_URL=http://127.0.0.1:8001/v1
ARTICLE_FOUNDRY_LLM_API_KEY=local
ARTICLE_FOUNDRY_LLM_MODEL=your-local-model
ARTICLE_FOUNDRY_PORT=8040
```

Arranca Article Foundry:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8040
```

Y abre la aplicación desde el navegador a través de localhost, SSH forwarding o el reverse proxy/túnel que tú configures.

---

## 🧪 Flujo de trabajo

### 1. 💡 Crea un proyecto

Cada proyecto mantiene sus propios fragmentos, conceptos, relaciones, fuentes y documentos generados.

### 2. ✍️ Alimenta la fundición

Pega una idea, párrafo, resultado, reflexión o fragmento. Puedes hacerlo durante días o semanas: no necesitas escribir el documento completo de una vez.

### 3. 📚 Añade las fuentes

Puedes conservar bibliografía junto con el conocimiento que estás construyendo.

### 4. 🧠 Deja crecer el mapa

Article Foundry extrae conceptos y construye relaciones entre el material acumulado.

### 5. 🏭 Compila

Selecciona el tipo de salida:

- 📰 **Divulgación:** contexto → problema → analogía → explicación → evidencia → implicaciones → cierre.
- 📄 **IEEE:** Title → Abstract → Keywords → Introduction → Related Work → Methodology → Experiments → Results → Discussion → Conclusion → References.
- 💡 **Patente:** Title → Technical Field → Background → Problem → Summary → Detailed Description → Embodiments → Figures → Claims → Abstract.

El resultado queda disponible como **LaTeX** y, cuando existe un compilador TeX compatible en el sistema, como **PDF**.

---

## 🌍 Idiomas

La interfaz y el flujo soportan múltiples idiomas, entre ellos:

🇲🇽 Español · 🇬🇧 English · 🇫🇷 Français · 🇮🇹 Italiano · 🇩🇪 Deutsch · 🇯🇵 日本語 · 🇨🇳 中文 · 🇮🇱 עברית · 🇦🇪 العربية · 🇷🇺 Русский · 🇰🇷 한국어

El idioma de entrada puede ser distinto del idioma del documento final.

---

## ☁️ Google Drive opcional

El repositorio incluye `deploy/drive_sync.py` para crear un snapshot de la base de datos y exportar proyectos/artefactos antes de sincronizarlos mediante `rclone`.

La integración es **opcional**. Configura tu propio remote y folder ID mediante variables de entorno. **No subas tokens OAuth, passwords, archivos `.env` privados ni configuración de `rclone` al repositorio.**

---

## 🔐 Privacidad y seguridad

La filosofía es que puedas ejecutar la cadena de generación en infraestructura que tú controles. Para un flujo realmente local debes usar también un **LLM local** y evitar configurar servicios externos que envíen tus datos fuera de la máquina.

Este repositorio **no contiene passwords, tokens OAuth, claves de Cloudflare ni credenciales de Google Drive**. Mantén esos secretos fuera de Git.

Si expones Article Foundry a Internet, protégelo con autenticación y HTTPS; no publiques directamente una instancia con proyectos privados sin una capa de acceso adecuada.

---

## 🧩 Integración sin invadir otros servicios

Article Foundry fue diseñado para vivir como servicio independiente. No necesita detener, reiniciar ni reconfigurar otros servidores de IA. Si ya tienes un LLM funcionando, simplemente consume su endpoint HTTP compatible.

---

## 🛠️ API principal

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

## 🤝 Haz tu propio Foundry

Clónalo, conecta **tu modelo local**, cambia el flujo editorial y conviértelo en tu propia memoria de investigación y escritura.

```bash
git clone https://github.com/LuisAlbertoMunozUbando/Article-Foundry.git
```

**💡 Tus ideas. 🧠 Tu modelo. 💻 Tu máquina. 🏭 Tu Foundry.**

---

Made with 🤖 + 🧠 + ☕ by **Alberto Muñoz**.
