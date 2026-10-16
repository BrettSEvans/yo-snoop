import subprocess
from yosnoop.setup_mac import setup_script

S = setup_script(owner="brettevanssf", owner_home="/Users/brettevanssf", shared="/Users/Shared/snoop")

def test_fails_fast():
    assert S.startswith("#!/bin/bash\nset -euo pipefail\n")

def test_refuses_preplanted_shared_path():
    assert '[ -L "$SHARED" ]' in S and 'SHARED="/Users/Shared/snoop"' in S
    assert 'stat -f %Su "$SHARED"' in S and "refusing" in S

def test_never_recurses_over_existing_shared_content():
    assert "chown -R" not in S.replace("chown -R snoop:snoop /Users/snoop", "")
    assert "chmod -R" not in S
    assert "install -d -o brettevanssf -g snoopread -m 750" in S

def test_snoop_has_own_primary_group_not_staff():
    assert "dseditgroup -o create snoop" in S
    assert "dscl . create /Users/snoop PrimaryGroupID" in S

def test_locks_owner_home():
    assert "chmod 700 /Users/brettevanssf" in S

def test_sudoers_is_narrow_validated_and_sets_home():
    assert "brettevanssf ALL=(snoop) NOPASSWD: /Users/Shared/snoop/bin/brain" in S
    assert "Defaults>snoop always_set_home" in S
    assert "visudo -cf" in S and "/etc/sudoers.d/snoop" in S
    assert "ALL=(ALL)" not in S and "ALL=(root)" not in S

def test_hidden_non_admin_user_with_no_shell():
    assert "sysadminctl -addUser snoop" in S and "-admin" not in S
    assert "IsHidden 1" in S and "/usr/bin/false" in S

def test_script_is_valid_bash(tmp_path):
    f = tmp_path / "s.sh"; f.write_text(S)
    assert subprocess.run(["bash", "-n", str(f)]).returncode == 0

def test_shared_dir_created_atomically_and_rechecked():
    assert 'mkdir -m 750 "$SHARED"' in S and "mkdir -p" not in S
    after = S.split("install -d -o", 1)[1]
    assert '[ -L "$SHARED" ]' in after and "refusing" in after
