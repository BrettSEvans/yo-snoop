import subprocess, sys


def test_importing_the_listener_helper_does_not_start_a_server():
    r = subprocess.run([sys.executable, "-c", "from spikes.p2_listen import last_sentence; print('ok')"],
                       capture_output=True, text=True, timeout=10)
    assert r.stdout.strip() == "ok"
