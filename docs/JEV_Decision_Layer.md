# TypeSafe JEV Decision Layer

Itachi uses JEV as a System One decision service, not as a prose/chat model.

## What JEV does

For each request JEV can make several typed judgments in one call:

- choose the task class: `general`, `code`, `research`, or `reasoning`;
- estimate whether fresh web information is materially useful;
- estimate whether Itachi's learned public knowledge corpus is likely to help.

Those decisions steer Itachi's existing provider ranking and evidence retrieval. The generative answer still comes from the configured answer-model pool.

If JEV is unavailable, times out, or returns an error, Itachi falls back to its built-in deterministic task classifier and existing web/retrieval behavior. JEV is therefore not a single point of failure.

## Configuration

The official endpoint is:

```
https://api.typesafe.ai/v1/systemone
```

Set the key only in a server-side secret:

```
TYPESAFE_API_KEY
```

For backward compatibility, `ITACHI_JEV_TOKEN` is also accepted.

Do not commit an API key to the public repository or expose it to browser JavaScript. The Streamlit app reads it from server-side secrets/environment variables.

## Request contract

Itachi sends `jev-latest` with a structured `state` and three typed questions: one `choice` plus two `noul` questions. JEV's returned probabilities are treated as advisory routing signals, not authorization to perform irreversible actions.

## Cost

JEV is inexpensive but should not be assumed to be permanently free. TypeSafe currently publishes a price for input tokens and free output tokens. Provider credits or launch allowances can change independently of Itachi.
