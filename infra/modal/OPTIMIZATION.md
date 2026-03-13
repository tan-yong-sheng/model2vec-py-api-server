# Modal Cold-Start Optimizations

This note captures what was done to reduce cold starts and why it helps.

## Applied Optimizations

1. Memory snapshots enabled
   - `enable_memory_snapshot=True` plus `@modal.enter(snap=True)`.
   - Pre-warms the process and reuses that state on subsequent cold starts.
   - Docs: https://modal.com/docs/guide/memory-snapshots

2. Preload the embedding model during snapshot warmup
   - The model is loaded before the snapshot is taken, so restores skip model initialization.
   - This reduces the cold-start path after scale-to-zero.
   - Docs: https://modal.com/docs/guide/memory-snapshots

3. Model cached on a Modal Volume
   - Model weights live on a volume mounted at `/app/models`.
   - Prevents repeated downloads and provides fast local reads.
   - Docs: https://modal.com/docs/guide/high-performance-llm-inference

4. Lean startup path and lazy filesystem access
   - Keep startup imports and file touches minimal to avoid slow cache tiers.
   - Modal’s container stack lazily loads image data; fewer reads means faster start.
   - Docs: https://modal.com/blog/jono-containers-talk

5. Scale-to-zero with snapshot restore
   - Cold-start latency is now mostly platform overhead (worker provisioning + restore).
   - Docs: https://modal.com/docs/guide/cold-start

## What to Expect

- First request after deploy still builds the snapshot and can be slower.
- Later cold starts (after idle) should be much faster because state is restored.
- If you need sub-second latency, use a warm pool (`min_containers > 0`).

## Estimated Cost (On-Demand, No Multipliers)

Using Modal on-demand pricing with 1 vCPU and 3 GiB RAM for 60 seconds:

- CPU: `0.0000131/core/sec * 1 * 60 = $0.000786`
- Memory: `0.00000222/GiB/sec * 3 * 60 = $0.0003996`
- Total: `$0.0011856` for 60 seconds (about 0.12 cents)

Pricing source: https://modal.com/pricing

## Where It Lives

- `infra/modal/modal_config.py`
- `src/app.py`
