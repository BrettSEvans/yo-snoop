from spikes.p1_meet_participants import classify

def test_signed_in():
    p = {"signedinUser": {"user": "users/123", "displayName": "Brett Evans"}}
    assert classify(p) == ("signed_in", "users/123", "Brett Evans")

def test_anonymous():
    assert classify({"anonymousUser": {"displayName": "Brett Evans"}}) == ("anonymous", None, "Brett Evans")

def test_phone():
    assert classify({"phoneUser": {"displayName": "+1 415"}}) == ("phone", None, "+1 415")

def test_unknown_shape_is_treated_as_anonymous():
    assert classify({}) == ("anonymous", None, "")
