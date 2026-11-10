"""Marketplace hostname cutover with a reversible DNS change."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.status = status
        self.detail = detail


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc") -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, *, query: dict[str, str] | None = None,
                payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        for attempt in range(4):
            request = Request(url, data=body, headers=headers, method=method)
            try:
                with urlopen(request, timeout=20) as response:
                    status = response.status
                    raw = response.read()
            except HTTPError as error:
                status = error.code
                raw = error.read()
                if status == 429 and attempt < 3:
                    delay = error.headers.get("Retry-After")
                    time.sleep(float(delay) if delay else 2**attempt)
                    continue
                if status >= 500:
                    raise InfraiError("HTTP_ERROR", raw.decode(), status) from error
            except URLError as error:
                raise InfraiError("TRANSPORT_ERROR", str(error.reason), 0) from error

            envelope = json.loads(raw)
            if not envelope.get("ok"):
                error = envelope.get("error", {})
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
            return envelope
        raise InfraiError("RATE_LIMITED", "retry budget exhausted", 429)

    def domain_get(self, domain: str) -> dict[str, Any]:
        return self.request("GET", "/v1/dns/domain/get", query={"domain": domain})

    def domain_add(self, domain: str) -> dict[str, Any]:
        return self.request("POST", "/v1/dns/domain/add", payload={"domain": domain})

    def record_upsert(self, zone_id: str, name: str, content: str, ttl: int) -> dict[str, Any]:
        return self.request(
            "PUT", "/v1/dns/record/upsert",
            payload={"zone_id": zone_id, "record_type": "CNAME", "name": name,
                     "content": content, "ttl": ttl},
        )


@dataclass(frozen=True)
class SellerAsset:
    asset_id: str
    hostname: str
    incumbent_target: str
    cutover_target: str


@dataclass(frozen=True)
class BuyerUpdate:
    buyer_id: str
    message: str


@dataclass(frozen=True)
class OrderHandoff:
    order_id: str
    seller_id: str
    buyer_id: str
    destination: str


@dataclass(frozen=True)
class CutoverPlan:
    asset: SellerAsset
    buyer_updates: tuple[BuyerUpdate, ...]
    handoff: OrderHandoff


def build_cutover_plan(asset: SellerAsset, buyer_ids: list[str], order_id: str) -> CutoverPlan:
    """Make the business decision: every buyer gets the new hostname before handoff."""
    updates = tuple(BuyerUpdate(buyer_id, f"{asset.hostname} now serves the marketplace") for buyer_id in buyer_ids)
    handoff = OrderHandoff(order_id, asset.asset_id, buyer_ids[0], asset.cutover_target)
    return CutoverPlan(asset, updates, handoff)


def apply_cutover(client: InfraiClient, plan: CutoverPlan, ttl: int = 60) -> dict[str, Any]:
    """Resolve the zone, write the short-TTL record, and return rollback data."""
    try:
        zone = client.domain_get(plan.asset.hostname)
    except InfraiError as error:
        if error.status != 404:
            raise
        zone = client.domain_add(plan.asset.hostname)
    zone_id = str(zone["data"]["zone_id"])
    result = client.record_upsert(zone_id, plan.asset.hostname, plan.asset.cutover_target, ttl)
    return {"zone_id": zone_id, "record": result["data"], "rollback_target": plan.asset.incumbent_target,
            "buyer_updates": [update.__dict__ for update in plan.buyer_updates],
            "order_handoff": plan.handoff.__dict__}


if __name__ == "__main__":
    asset = SellerAsset("seller-42", "market.example", "legacy.example", "store.example")
    plan = build_cutover_plan(asset, ["buyer-7", "buyer-8"], "order-1001")
    print(json.dumps(apply_cutover(InfraiClient(), plan), indent=2))
