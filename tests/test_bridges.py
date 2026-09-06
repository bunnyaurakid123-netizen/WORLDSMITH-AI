from worldsmith.generation.bridges import BridgeReport


def test_bridge_report_contract():
    report = BridgeReport(blocks_changed=42, supports=3, deck_blocks=24, rail_blocks=18)
    assert report.blocks_changed == report.deck_blocks + report.rail_blocks
    assert report.supports == 3
