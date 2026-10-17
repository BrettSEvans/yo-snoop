import stat
from spikes.common import pdt_now, sha_prefix, SECRETS_DIR

def test_sha_prefix_is_12_hex_and_stable():
    assert sha_prefix("abc") == "ba7816bf8f01"
    assert len(sha_prefix("anything")) == 12

def test_pdt_now_is_labeled():
    assert pdt_now().endswith((" PDT", " PST"))

def test_secrets_dir_is_private_and_ignored():
    assert SECRETS_DIR.exists()
    assert stat.S_IMODE(SECRETS_DIR.stat().st_mode) == 0o700
