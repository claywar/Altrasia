"""3D position derivation and layout upgrade."""

from altrasia.domain.position3d import derive_position3d, upgrade_layout_v1


def test_derive_position3d_from_map_level():
    node = {"mapLevel": 2, "layout": {"x": 50, "y": 50}}
    p = derive_position3d(node, {})
    assert p["z"] == 6.0
    assert p["x"] == 0.0


def test_upgrade_layout_adds_position3d():
    layout = {
        "schemaVersion": 1,
        "scope": "mini",
        "nodes": [{"sceneId": "a", "mapPosition": {"x": 40, "y": 60}, "mapLevel": 1}],
    }
    out = upgrade_layout_v1(layout)
    assert out["schemaVersion"] == 2
    nodes = out["nodes"]
    assert nodes[0].get("position3d")
    assert nodes[0]["position3d"]["z"] == 3.0
