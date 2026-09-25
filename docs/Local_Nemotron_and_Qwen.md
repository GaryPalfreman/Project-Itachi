# Local Nemotron and Qwen

This setup uses a model server on the same computer as the FastAPI app. Itachi calls Ollama over loopback; model weights stay on that computer. The hosted Streamlit app cannot access a file in your Downloads folder. See [[Deployment_Mac]] and [[Hosted_Testing]].

## Identify the Nemotron file first

`model.safetensors` is a generic weight filename, not a model identifier. Its header and adjacent `config.json`, tokenizer and possibly other weight shards determine what it is. The repo does not contain your Downloads file; do not upload weights to this public repository or substitute a random config from another Nemotron release.

On the Mac that actually has the file, from the project directory:

```bash
python3 scripts/inspect_local_weights.py "$HOME/Downloads/model.safetensors"
ls -lh "$HOME/Downloads"/{model.safetensors,config.json,tokenizer.json,tokenizer_config.json,model.safetensors.index.json} 2>/dev/null
```

The inspector reads only the bounded safetensors JSON header and nearby config files; it does not load tensors or contact a server. The supplied file has **2,281,852,472 bytes, 146 tensors, and no adjacent config or tokenizer**. NVIDIA publishes a `model.safetensors` with exactly that size for **Nemotron-3-Embed-1B-BF16**. Size is a clue, not proof. Verify the full SHA-256 before assuming it is that release:

```bash
python3 "$HOME/Project-Itachi/scripts/inspect_local_weights.py" \
  "$HOME/Downloads/model.safetensors" --sha256
```

The expected official checksum is `f959c3b04e66b42de280bfb97c140cb7e0bfe25e3ecb0b4464c68a8436b2d04f`. This reads the complete 2.28 GB file locally, without uploading it. If `verified_match` is `null`, stop: identify the original download URL and model revision first. An adapter needs its matching base model. Do not invent config or tokenizer files.

**Nemotron-3-Embed-1B-BF16 generates retrieval vectors, not chat responses.** If the checksum matches, its useful role in Itachi is semantic search over an explicitly enabled, nonpersonal local knowledge folder. It cannot be configured as `ITACHI_REASONING_MODEL` or used with the chat-completions route.

After a checksum match, use the included preparation script to fetch the small companion files from NVIDIA's pinned Hugging Face revision. It reuses your existing weights through a local symlink and writes outside the GitHub clone:

```bash
cd "$HOME/Project-Itachi"
python3 -m pip install huggingface_hub
python3 -m scripts.prepare_local_embed \
  "$HOME/Downloads/model.safetensors" "$HOME/Models/itachi-nemotron-embed"
```

This command contacts Hugging Face for model metadata and tokenizer files only. It never uploads your weights. A successful preparation does not turn an embedding model into a chat model. Semantic vault retrieval is a separate opt-in feature and requires a local embedding runtime; the current default keyword search does not load these weights. Never enable knowledge access for personal documents under this project's current settings.

For a **separate chat model** from NVIDIA, pull a published Ollama Nemotron variant:

```bash
ollama pull nemotron-mini:4b
```

That pull is **not** the same as importing your Downloads checkpoint. Ollama can import complete supported safetensors model directories, but the incomplete, unidentified file in Downloads is not such a directory.

## Add Qwen fallback

```bash
ollama pull qwen3:4b
ollama list
curl -sS http://127.0.0.1:11434/v1/models
```

For Nemotron Mini chat and Qwen fallback, set these entries in your **local** `.env`:

```dotenv
ITACHI_REASONING_URL=http://127.0.0.1:11434/v1
ITACHI_REASONING_MODEL=nemotron-mini:4b
ITACHI_FALLBACK_URL=http://127.0.0.1:11434/v1
ITACHI_FALLBACK_MODEL=qwen3:4b
```

Restart FastAPI after the change and ask a text question. Selected quota, transport, context and server failures can move the answer to Qwen. Bad credentials and incompatible model responses surface as errors. The local backend uses `ITACHI_MODEL_ROUTES_JSON` for up to five routes when more than two models are needed; see [[Internet_and_Accounts]]. Do not put a Downloads file path or a loopback URL in hosted Streamlit secrets.

## Project capability profiles

Itachi's `web_search`, `github_search`, `calculate` and `request_access` tools are bounded in [[Autonomy_and_Permissions]]. Before adding any third-party agent or skill, verify its actual download URL, license, version, permissions and executable scripts. `hugginbay.xyz` could not be verified from a reachable official listing during this build, so no code from that domain was added or executed. A repository name alone cannot grant tool or account access.

## References

- [Ollama import procedure](https://docs.ollama.com/import)
- [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility)
- [Qwen3:4b in Ollama](https://ollama.com/library/qwen3:4b)
- [Nemotron Mini in Ollama](https://ollama.com/library/nemotron-mini)
- [NVIDIA Nemotron-3-Embed-1B-BF16 model card](https://huggingface.co/nvidia/Nemotron-3-Embed-1B-BF16)
- [Exact safetensors checksum at NVIDIA's repository](https://huggingface.co/nvidia/Nemotron-3-Embed-1B-BF16/blob/18abd04873998492fdbb52aa48eb4bdde53c3593/model.safetensors)
