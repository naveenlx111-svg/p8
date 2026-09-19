import pytest

from backend.runtime.android import AndroidSession, parse_hierarchy


HIERARCHY = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<hierarchy rotation="0">
  <node index="0" text="" class="android.widget.FrameLayout" package="com.example.shop"
        content-desc="" clickable="false" enabled="true" focusable="false" bounds="[0,0][1080,1920]">
    <node index="0" text="Checkout" class="android.widget.TextView" package="com.example.shop"
          content-desc="" clickable="false" enabled="true" focusable="false" bounds="[40,60][400,120]" />
    <node index="1" text="" class="android.widget.EditText" package="com.example.shop"
          content-desc="Email address" clickable="true" enabled="true" focusable="true" focused="true"
          password="false" bounds="[40,180][900,280]" />
    <node index="2" text="" class="android.widget.ImageButton" package="com.example.shop"
          content-desc="" clickable="true" enabled="true" focusable="true" bounds="[20,320][55,355]" />
  </node>
</hierarchy>"""


def test_android_hierarchy_becomes_ephemeral_semantic_observation():
    observation, raw = parse_hierarchy(HIERARCHY, "obs-1", "emulator-5554", "com.example.shop", ".Checkout")
    assert observation.url.startswith("android://emulator-5554/com.example.shop")
    assert observation.heading == "Checkout"
    assert observation.visible_text == "Checkout\nEmail address"
    assert observation.total_interactive == 2
    assert observation.elements[0].role == "textbox"
    assert observation.elements[0].name == "Email address"
    assert observation.elements[0].focused is True
    assert observation.elements[1].role == "button"
    assert observation.elements[1].name == ""
    assert len(raw) == 4


@pytest.mark.asyncio
async def test_android_audit_uses_accessibility_tree_and_touch_geometry(tmp_path):
    session = AndroidSession(tmp_path, "emulator-5554", "com.example.shop")
    _, session._raw_nodes = parse_hierarchy(
        HIERARCHY, "obs-1", "emulator-5554", "com.example.shop", ".Checkout",
    )
    session.density = 1.0
    violations = {violation.id: violation for violation in await session.audit()}
    assert violations["android-missing-label"].total_nodes == 1
    assert violations["android-touch-target-size"].total_nodes == 1
    assert "35dp" in violations["android-touch-target-size"].nodes[0].failure_summary

