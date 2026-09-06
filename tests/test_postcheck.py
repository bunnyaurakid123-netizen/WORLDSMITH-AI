from worldsmith.generation.postcheck import PostBuildVerifier


class FakeLevel:
    class Wrapper:
        platform = "java"
        max_world_version = (1, 20, 4)

    level_wrapper = Wrapper()

    def get_version_block(self, x, y, z, dimension, version):
        if (x, y, z) in {(0, 101, 0), (8, 101, 0), (0, 125, 0)}:
            return "minecraft:stone", None
        return "minecraft:air", None


def test_postcheck_finds_occupied_structure_samples():
    verifier = PostBuildVerifier(FakeLevel())
    report = verifier.verify({
        "builds": [{"x": 0, "y": 100, "z": 0, "width": 16, "depth": 16, "height": 24}],
        "roads": [],
    })
    assert report.checked_structures == 1
    assert report.passed
    assert not report.issues
