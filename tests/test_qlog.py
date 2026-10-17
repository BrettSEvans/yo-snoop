import datetime, json, pytest
from yosnoop import qlog

E = {"ts": 1.0, "asker": "Brett Evans", "room": "desk", "question": "CI?", "outcome": "spoken", "latency_s": 2.1}

def test_write_has_exact_fields(tmp_path):
    qlog.write(E, tmp_path, today=datetime.date(2026, 10, 9))
    assert set(json.loads((tmp_path / "questions-2026-10-09.ndjson").read_text())) == set(qlog.FIELDS)

def test_write_rejects_extra_fields(tmp_path):
    with pytest.raises(ValueError):
        qlog.write({**E, "transcript": "room talk"}, tmp_path)

def test_prune_keeps_seven_days(tmp_path):
    for d in ("2026-09-30", "2026-10-02", "2026-10-09"):
        (tmp_path / f"questions-{d}.ndjson").write_text("{}")
    qlog.prune(tmp_path, days=7, today=datetime.date(2026, 10, 9))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["questions-2026-10-02.ndjson", "questions-2026-10-09.ndjson"]

def test_log_dir_is_private(tmp_path):
    qlog.write(E, tmp_path / "logs")
    assert oct((tmp_path / "logs").stat().st_mode & 0o777) == "0o700"
