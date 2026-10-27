from yosnoop.prepare import prepare_config

def test_no_registry_cmd_without_bundle(tmp_path):
    cfg = prepare_config(knowledge=tmp_path, bundle_built=False, runtime=tmp_path / "rt", serena_cmd=["serena"], persona="p")
    assert "registry_cmd" not in cfg and cfg["serena_cmd"] == ["serena"]

def test_registry_cmd_with_bundle_uses_runtime_node(tmp_path):
    cfg = prepare_config(knowledge=tmp_path, bundle_built=True, runtime=tmp_path / "rt", serena_cmd=None, persona="p")
    assert cfg["registry_cmd"] == [str(tmp_path / "rt" / "node" / "bin" / "node"),
                                   str(tmp_path / "rt" / "registry-mcp" / "out" / "index.js")]


def test_run_sync_works_inside_a_running_event_loop():  # ./snoop desk calls prepare from async code (2026-10-27)
    import asyncio
    from yosnoop.prepare import run_sync
    async def answer(): return 42
    async def desk(): return run_sync(answer())
    assert run_sync(answer()) == 42 and asyncio.run(desk()) == 42
