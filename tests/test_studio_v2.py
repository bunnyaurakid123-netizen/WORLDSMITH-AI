from pathlib import Path

from worldsmith.studio_v2 import BuildWorker


def test_build_worker_keeps_world_path_and_plan():
    plan = {
        'seed': 42,
        'center': [0, 100, 0],
        'terrain': {'enabled': False},
        'builds': [],
    }
    worker = BuildWorker(Path('example-world'), plan, True)
    assert worker.path == Path('example-world')
    assert worker.plan['seed'] == 42
    assert worker.do_backup is True
