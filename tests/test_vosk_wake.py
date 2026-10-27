import hashlib, io, zipfile
import pytest
from yosnoop.desk import vosk_wake
from yosnoop.desk.vosk_wake import decide, files_ok, fetch


def w(word, conf=1.0, start=0.0, end=0.1):
    return {"word": word, "conf": conf, "start": start, "end": end}


def test_wakes_on_yo_snoop_first():
    assert decide([w("[unk]", 0.86, 0.0, 0.06), w("yo", 1.0, 0.06, 0.2), w("snoop", 1.0, 0.24, 0.6), w("[unk]", 1.0, 0.87, 2.0)])


def test_no_wake_when_speech_comes_before():  # "I said yo snoop earlier but never mind"
    assert not decide([w("[unk]", 1.0, 0.0, 0.4), w("yo", 1.0, 0.42, 0.6), w("snoop", 1.0, 0.63, 0.9)])


def test_no_wake_on_bare_snoop_or_other_first_word():
    assert not decide([w("snoop", 1.0, 0.06, 0.4), w("[unk]", 1.0, 0.39, 1.5)])
    assert not decide([w("[unk]", 1.0, 0.0, 0.05), w("snoop", 1.0, 0.1, 0.4), w("yo", 1.0, 0.5, 0.6), w("snoop", 1.0, 0.6, 0.9)])
    assert not decide([])


def test_no_wake_when_unsure():
    assert not decide([w("yo", 0.55, 0.1, 0.2), w("snoop", 1.0, 0.2, 0.5)])
    assert decide([w("yo", 0.6, 0.1, 0.2), w("snoop", 0.6, 0.2, 0.5)])


def _zip_bytes():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(f"{vosk_wake.MODEL_NAME}/README", "model")
    return buf.getvalue()


def test_fetch_verifies_and_unpacks(tmp_path, monkeypatch):
    data = _zip_bytes()
    monkeypatch.setattr(vosk_wake, "ZIP_SHA256", hashlib.sha256(data).hexdigest())
    assert not files_ok(tmp_path)
    assert fetch(tmp_path, download=lambda url, dest: dest.write_bytes(data))
    assert files_ok(tmp_path) and (tmp_path / vosk_wake.MODEL_NAME / "README").read_text() == "model"
    assert not list(tmp_path.glob("*.zip"))


def test_fetch_rejects_a_bad_download(tmp_path):
    assert not fetch(tmp_path, download=lambda url, dest: dest.write_bytes(_zip_bytes()))
    assert not files_ok(tmp_path) and not (tmp_path / vosk_wake.MODEL_NAME).exists()


def test_make_vosk_wake_is_none_without_the_model(tmp_path):
    assert vosk_wake.make_vosk_wake(tmp_path) is None


@pytest.mark.slow
def test_real_model_loads_and_rejects_silence():
    import numpy as np
    vw = vosk_wake.make_vosk_wake()
    if vw is None:
        pytest.skip("Vosk model not installed (./snoop voice-setup)")
    woke, heard = vw.check(np.zeros(16000, np.float32))
    assert woke is False
