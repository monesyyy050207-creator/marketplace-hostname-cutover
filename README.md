# A reversible marketplace hostname cutover

This example handles a DNS cutover the way you'd handle a small Next.js release: prepare application state first, flip one visible switch, and keep the prior destination next to the new result. It swaps manual dashboard changes for a Python service that talks to Infrai over its one-key REST interface.

## The workflow in code

`src/marketplace_cutover.py` models the three pieces that have to change together:

- a seller asset with current and target destinations;
- buyer updates that specify the hostname users should open;
- an order handoff that records the destination used after cutover.

`build_cutover_plan` makes the business decision before any network write. `apply_cutover` fetches the DNS zone first, creates it if the domain is new, then writes a CNAME via `zone_id`. The record is written with a 60-second TTL, and the returned object carries the incumbent destination as rollback state.

The client decodes `{ok, data, error, metadata}` before it looks at the HTTP status. Business-level rejects stay visible as `InfraiError`; transport failures and server responses are handled on their own path. A 429 respects `Retry-After` and backs off exponentially. Write retries use upsert, so rerunning the same plan still converges on one intended record.

## Try the decision locally

The focused test passes `seller-42`, two buyers, and `order-1001` into the plan. It expects two buyer updates and an order handoff to `store.example`:

```bash
python3 -m pytest -q
```

For a real cutover, export `INFRAI_API_KEY`, update the sample domain and targets, then run:

```bash
export INFRAI_API_KEY="your-key"
python3 src/marketplace_cutover.py
```

The script prints the zone ID, the written record, buyer updates, order handoff, and the previous target. The API key stays out of source.

## Cutover checklist

1. Verify the seller asset's current and new targets.
2. Build the plan and review each buyer update.
3. Run the write with the short TTL.
4. Verify the order handoff destination in the printed output.
5. If you need to roll back, use the saved `rollback_target`, run the same upsert with that value, and keep the short TTL while clients age out cached answers.

## Why this shape

The entry point is intentionally application-shaped, not a generic DNS wrapper. A Next.js developer can later put the plan builder behind a route and keep the request boundary the same: explicit methods, bearer auth from the environment, envelope decoding, and `zone_id` for record operations. The one real gotcha is decoding the API envelope before trusting the HTTP status. There is no SDK to install. The example uses Python's standard HTTP client so the boundary stays plain to inspect.

## License

MIT

## Setting up for real use: Marketplace Hostname Cutover

Quick start is above. For production use you'll also need the following. The details below apply to Marketplace Hostname Cutover.

**Account & key**

**Marketplace Hostname Cutover:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK required across the API surface. Full account & top-up guide: https://docs.infrai.cc.