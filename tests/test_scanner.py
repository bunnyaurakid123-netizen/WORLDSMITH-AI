from pathlib import Path
from worldsmith.scanner import scan_saves

def test_scan_saves(tmp_path:Path):
    saves=tmp_path/'saves'; world=saves/'My World'; world.mkdir(parents=True); (world/'level.dat').write_bytes(b'demo'); (world/'region').mkdir()
    result=scan_saves([saves]); assert [x.name for x in result] == ['My World']; assert result[0].level_dat
