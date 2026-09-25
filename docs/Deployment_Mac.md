# Deployment on Apple Silicon Mac

From the extracted `itachi` directory:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r backend/requirements-voice.txt
cp .env.example .env
```

Install [Ollama for macOS](https://ollama.com/download/mac) and then run:

```bash
ollama pull llama3.2:3b
ollama list
python3 scripts/local_inventory.py
```

The default model matches the previously configured lightweight model on your M2 Mac. The inventory checks the vault path and Ollama's local model list without changing either. Select an installed Nemotron, Qwen or DeepSeek variant by updating `ITACHI_REASONING_MODEL` in `.env`; larger models can exhaust the 8 GB shared memory. Set `ITACHI_FALLBACK_URL=http://127.0.0.1:11434/v1` and `ITACHI_FALLBACK_MODEL` to another **installed** Ollama model for local fallback. A separate hosted compatible endpoint can also serve as fallback if you deliberately configure it. For up to five routes, set `ITACHI_MODEL_ROUTES_JSON` in `.env` to the JSON array described in [[Hosted_Testing]]; it overrides the reasoning/fallback pair for the local face's reasoning route too.

Install a Piper voice from the active upstream project:

```bash
source .venv/bin/activate
python -m piper.download_voices en_US-lessac-medium
python -m piper -m en_US-lessac-medium -f /tmp/itachi-voice.wav -- 'Voice system ready.'
```

Keep the downloaded voice files in that directory, or set `ITACHI_PIPER_VOICE` to the full `.onnx` path. Edit `.env` to point `ITACHI_VAULT` to a real Obsidian vault path; start with the bundled example vault if you want to inspect the system first. On the first STT request, faster-whisper downloads its selected model; subsequent runs use its local cache. Microphone access requires browser permission.

Run from the `itachi` project root:

```bash
PYTHONPATH=backend python -m unittest discover -s backend/tests -v
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765/`; check `http://127.0.0.1:8765/api/health`. Send a text prompt first, then try MIC and VOICE ON. If the model returns a 404, check `ollama list` and the exact configured model name. If voice fails, check the downloaded `.onnx` and `.onnx.json` files and the Piper command above.

## Codex, OpenClaw and JEV

Codex is configured only if you have an authorized OpenAI-compatible coding endpoint: put its full `/v1` base URL, model name and server-side key into `.env`. A local Codex CLI installation by itself does not provide this endpoint. An alternative local coding model can use Ollama's compatible endpoint.

OpenClaw exposes an optional HTTP chat completions API. Its endpoint is disabled by default. If you choose to enable it, add the following property to the existing `gateway` object in your OpenClaw configuration, preserving its other settings. The existing production OpenClaw configuration and vault should remain untouched until you intentionally perform that change:

```json5
gateway: {
  http: { endpoints: { chatCompletions: { enabled: true } } }
}
```

Keep the gateway on loopback. Confirm that `curl -sS http://127.0.0.1:18789/v1/models -H "Authorization: Bearer YOUR_GATEWAY_TOKEN"` lists `openclaw/default`, then set `ITACHI_OPENCLAW_URL=http://127.0.0.1:18789/v1` and `ITACHI_OPENCLAW_TOKEN` in `.env`. The token carries operator-level access; do not publish this server without adding authentication. The route calls `openclaw/default`.

JEV AI needs an actual endpoint or a small bridge implementing the Itachi adapter contract in [[Master_Architecture_Blueprint]]. Set URL and token only after testing the bridge. Without them the research route reports an explicit configuration error. Source dates and URLs should be included in `sources`.

To test a cloud-accessible version before local hardware is ready, use [[Hosted_Testing]]. That console can switch to a separately configured Llama-compatible provider after a recognized rate, context or availability failure. The local UI can use the same fallback settings from `.env`.

## References

- [OpenClaw HTTP chat completions](https://docs.openclaw.ai/gateway/openai-http-api)
- [Piper active upstream](https://github.com/OHF-Voice/piper1-gpl)
- [faster-whisper upstream](https://github.com/SYSTRAN/faster-whisper)
- [Ollama Nemotron model](https://ollama.com/library/nemotron-mini)
