# Itachi · Local Assistant System

Start with [[Master_Architecture_Blueprint]], then [[Deployment_Mac]], [[Protocol_and_State_Rules]], and [[Agent_Assignments]]. These files live in `docs/` and can be copied into an Obsidian vault. The system itself reads the configured vault.

Fast start: create a Python virtual environment, install `backend/requirements-voice.txt`, copy `.env.example` to `.env`, pull `nemotron-mini:4b` with Ollama, and run `python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8765`. See [[Deployment_Mac]] for the full sequence.

This is a local prototype. It includes the face, voice routes, model adapters and vault read/new-note API. It does not include verified JEV API connectivity, an authenticated internet deployment, or automatic coding agent execution.

The `/api/graph` endpoint extracts wiki-links between existing Markdown notes. GitHub Actions checks Python, API routes, vault behavior, and JavaScript syntax on each push.

For a web-based test before local hardware is ready, run `streamlit_app.py` on [Streamlit Community Cloud](https://share.streamlit.io/). See [[Hosted_Testing]] for private access, model secrets, and read-only vault import. The full UI still runs through FastAPI on a local or protected Docker host.
