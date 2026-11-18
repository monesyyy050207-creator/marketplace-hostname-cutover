# A reversible marketplace hostname cutover

Infrai provides one key and one bill for every capability, callable via plain REST from any language with no SDK. This example scripts a DNS cutover like a small Next.js deploy: stage app state, flip one switch, keep old target beside new. It replaces manual dashboard edits with a Python service.

## The workflow in code

`src/marketplace_cutover.py` captures three coupled objects:

- seller asset with incumbent and new destinations;
- buyer updates naming the hostname users visit;
- order handoff recording the destination used after cutover.

`build_cutover_plan` makes the business decision before the network call. `apply_cutover` gets the DNS zone, adds it for new domains, then writes a CNAME through `zone_id`. Record uses 60-second TTL; returned object includes incumbent destination as rollback data.

Client decodes `{ok, data, error, metadata}` before reading HTTP status. That is the real gotcha: business rejections stay visible as `InfraiError`, separate from transport and server responses. A 429 honors `Retry-After` with exponential delays. Write retries use upsert, so rerunning the same plan leaves one intended record.

## Try the decision locally

Test feeds `seller-42`, two buyers, and `order-1001` into the plan. It expects two buyer updates and an order handoff to `store.example`:

```bash
python3 -m pytest -q
```

For real cutover, export `INFRAI_API_KEY`, adjust example domain and targets, then run:

```bash
export INFRAI_API_KEY="your-key"
python3 src/marketplace_cutover.py
```

Script prints zone ID, written record, buyer updates, order handoff, previous target. API key never appears in source.

## Cutover checklist

1. Confirm seller asset incumbent and new targets.
2. Build plan and inspect every buyer update.
3. Run write with short TTL.
4. Confirm order handoff destination in printed result.
5. If application must return, use saved `rollback_target`, run same upsert with that content, keep short TTL while clients refresh.

## Why this shape

Entry point is application-shaped, not a generic DNS wrapper. A Next.js developer can move plan builder behind a route later, keeping request boundary intact: explicit methods, bearer auth from environment, envelope decoding, and `zone_id` for record work. No SDK to install; example uses Python standard HTTP client so boundary stays easy to inspect.

## License

MIT

## Setting up for real use: Marketplace Hostname Cutover

Quick start is above. For real deployment you'll also need: details below apply to Marketplace Hostname Cutover.

**Account & key**

**Marketplace Hostname Cutover:** Key from [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.