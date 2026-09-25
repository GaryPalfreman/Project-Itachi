# Local Nemotron and Qwen

This setup uses a model server on the same computer as the FastAPI app. Itachi calls Ollama over loopback; model weights stay on that computer. The hosted Streamlit app cannot access a file in your Downloads folder. See [[Deployment_Mac]] and [[Hosted_Testing]].

## Identify the Nemotron file first

`model.safetensors` is a generic weight filename, not a model identifier. Its header and adjacent `config.json`, tokenizer and possibly other weight shards determine what it is. The repo does not contain your Downloads file; do not upload weights to this public repository or substitute a random config from another Nemotron release.

On the Mac that actually has the file, from the project directory:

```bash
python3 scripts/inspect_local_weights.py "$HOME/Downloads/model.safetensors"
ls -lh "$HOME/Downloads"/{model.safetensors,config.json,tokenizer.json,tokenizer_config.json,model.safetensors.index.json} 2>/dev/null
```

The inspector reads only the bounded safetensors JSON header and nearby config files; it does not load tensors or contact a server. If `model_type` is `unknown`, `adapter` is `true`, the required files are missing, or the filename is one shard of a larger checkpoint, find the **exact original model repository and revision** before import. An adapter needs its matching licensed base model. A valid set of files may still require an architecture that the installed Ollama version does not support. Check disk space and available memory before importing.

If the original complete checkpoint directory is confirmed to contain an Ollama-supported model, create a local Modelfile pointing to the **directory**, not the one `.safetensors` file:

```bash
printf 'FROM %s\n' "$HOME/Downloads" > "$HOME/Downloads/Modelfile.itachi"
ollama create itachi-nemotron -f "$HOME/Downloads/Modelfile.itachi"
ollama run itachi-nemotron 'Reply with a single sentence identifying your model family.'
```

The model's self-report is only a smoke test; confirm the actual identity and redistribution license from its original model card. If the importer rejects this architecture, use a separately published compatible Nemotron model while we establish the file's provenance:

```bash
ollama pull nemotron-mini:4b
```

That pull is **not** the same as importing your Downloads checkpoint.

## Add Qwen fallback

```bash
ollama pull qwen3:4b
ollama list
curl -sS http://127.0.0.1:11434/v1/models
```

For an imported Nemotron, set these entries in your **local** `.env`:

```dotenv
ITACHI_REASONING_URL=http://127.0.0.1:11434/v1
ITACHI_REASONING_MODEL=itachi-nemotron
ITACHI_FALLBACK_URL=http://127.0.0.1:11434/v1
ITACHI_FALLBACK_MODEL=qwen3:4b
```

If using the official separate Nemotron Mini pull, set `ITACHI_REASONING_MODEL=nemotron-mini:4b` instead. Restart FastAPI after the change and ask a text question. Selected quota, transport, context and server failures can move the answer to Qwen. Bad credentials and incompatible model responses surface as errors. The local backend uses `ITACHI_MODEL_ROUTES_JSON` for up to five routes when more than two models are needed; see [[Internet_and_Accounts]]. Do not put a Downloads file path or a loopback URL in hosted Streamlit secrets.

## Project capability profiles

Itachi's `web_search`, `github_search`, `calculate` and `request_access` tools are bounded in [[Autonomy_and_Permissions]]. Before adding any third-party agent or skill, verify its actual download URL, license, version, permissions and executable scripts. `hugginbay.xyz` could not be verified from a reachable official listing during this build, so no code from that domain was added or executed. A repository name alone cannot grant tool or account access.

## References

- [Ollama import procedure](https://docs.ollama.com/import)
- [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility)
- [Qwen3:4b in Ollama](https://ollama.com/library/qwen3:4b)
- [Nemotron Mini in Ollama](https://ollama.com/library/nemotron-mini)
