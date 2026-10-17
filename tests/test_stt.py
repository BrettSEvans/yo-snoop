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
