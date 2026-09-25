# Itachi · Local Assistant System

Start with [[Master_Architecture_Blueprint]], then [[Autonomy_and_Permissions]], [[Public_Learning_and_Recovery]], [[Deployment_Mac]], [[Hosted_Testing]], [[Internet_and_Accounts]], [[Protocol_and_State_Rules]], and [[Agent_Assignments]]. These files live in `docs/`.

Fast start: create a Python virtual environment, install `backend/requirements-voice.txt`, copy `.env.example` to `.env`, run `python3 scripts/local_inventory.py` to inspect your Mac, and run `python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8765`. See [[Deployment_Mac]] for the full sequence.

This is a local prototype. It includes the face, voice routes, task-aware model routing, optional free-model discovery, a no-model public-reference mode, bounded autonomous research and a scheduled public source catalog. Model access still needs an authorized provider or a local runtime. Personal knowledge is disabled by default, and the hosted app has no note importer. Account registration and CAPTCHA handling are not automated.

Free AI and storage provider status: [[Free_Provider_Assessment]].

Local Nemotron checkpoint inspection and Qwen setup: [[Local_Nemotron_and_Qwen]].

The `/api/graph` endpoint extracts wiki-links between existing Markdown notes. GitHub Actions checks Python, API routes, vault behavior, and JavaScript syntax on each push.

For a web-based test before local hardware is ready, run `streamlit_app.py` on [Streamlit Community Cloud](https://share.streamlit.io/). See [[Hosted_Testing]] for private access and model secrets. The full UI still runs through FastAPI on a local or protected Docker host.

Cloud-native learning, multi-provider failover and recovery: [[Cloud_Growth_and_Recovery]].
