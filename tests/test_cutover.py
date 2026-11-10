import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from marketplace_cutover import SellerAsset, build_cutover_plan


def test_cutover_notifies_buyers_before_order_handoff():
    asset = SellerAsset("seller-42", "market.example", "legacy.example", "store.example")
    plan = build_cutover_plan(asset, ["buyer-7", "buyer-8"], "order-1001")

    assert [item.buyer_id for item in plan.buyer_updates] == ["buyer-7", "buyer-8"]
    assert plan.handoff.destination == "store.example"
    assert plan.handoff.order_id == "order-1001"
