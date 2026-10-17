import pytest
from yosnoop.wake import is_wake, is_stop
from tests.helpers import say_to_array

@pytest.fixture(scope="module")
def stt():
    from yosnoop.desk.stt import Transcriber
    return Transcriber()

@pytest.mark.slow
def test_wake_phrase_survives_transcription(stt):
    assert is_wake(stt.transcribe(say_to_array("Yo Snoop, how many pull requests merged yesterday?")))

@pytest.mark.slow
def test_stop_phrase_survives_transcription(stt):
    assert is_stop(stt.transcribe(say_to_array("Okay, peanut butter.")))

@pytest.mark.slow
def test_decoy_is_not_a_wake(stt):
    assert not is_wake(stt.transcribe(say_to_array("We should snoop around the logs later.")))


def test_transcriber_biases_toward_the_wake_word():
    from yosnoop.desk import stt as m
    calls = {}
    class FakeModel:
        def transcribe(self, audio, **kw): calls.update(kw); return iter([]), None
    import threading
    t = m.Transcriber.__new__(m.Transcriber); t.m = FakeModel(); t._lock = threading.Lock()
    import numpy as np
    t.transcribe(np.zeros(16000, np.float32))
    assert calls["hotwords"] == "Snoop"
