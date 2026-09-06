from worldsmith.generation.redstone import RedstoneReport


def test_redstone_report_contract():
    report = RedstoneReport(blocks_changed=11, components=11, valid=True, message="ok")
    assert report.valid
    assert report.components == 11
    assert report.blocks_changed == 11
