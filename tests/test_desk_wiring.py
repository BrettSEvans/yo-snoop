import asyncio
from yosnoop.brain_client import BrainReply
from yosnoop.desk.run import DeskCtx, handle_utterance
from yosnoop.desk.state import DeskState

class Brain:
    def __init__(self, reply, delay=0.0): self.reply, self.asked, self.delay = reply, [], delay
    async def ask(self, q, asker, room):
        self.asked.append((q, asker, room)); await asyncio.sleep(self.delay); return self.reply

class Spk:
    def __init__(self, per=0.0): self.said, self.stopped, self.per, self._stop = [], 0, per, False
    async def speak(self, ss, on_start, on_end):
        self._stop = False; on_start()
        for s in ss:
            if self._stop: break
            self.said.append(s); await asyncio.sleep(self.per)
        on_end()
        return self._stop
    async def play_clip(self, audio, rate, on_start, on_end):
        on_start(); self.said.append("<rustle>"); await asyncio.sleep(self.per); on_end(); return False
    async def stop(self): self.stopped += 1; self._stop = True

def ctx(reply, delay=0.0, per=0.0, dry=False, acks=(), think_gap=None):  # no acks or sounds: tests about the answer
    printed, logs = [], []
    c = DeskCtx(state=DeskState(), brain=Brain(reply, delay), speaker=Spk(per), host_name="Brett Evans",
                log=logs.append, print_fn=printed.append, dry=dry, acks=acks, think_gap=think_gap)
    return c, printed, logs

def test_question_is_answered_spoken_and_printed():
    c, printed, logs = ctx(BrainReply(True, "One. Two. Three. Four.", 60, None))
    asyncio.run(handle_utterance(c, "Yo Snoop, CI?", 1.0, 2.0))
    assert c.brain.asked == [("CI?", "Brett Evans", "desk")]
    assert c.speaker.said == ["Snoop here.", "One.", "Two.", "Three."]
    assert printed[-1].endswith("One. Two. Three. Four.")
    assert logs[0]["outcome"] == "spoken" and logs[0]["question"] == "CI?"

def test_secret_answer_is_blocked():
    c, printed, _ = ctx(BrainReply(True, "key " + "ghp_" + "Q" * 36, 60, None))
    asyncio.run(handle_utterance(c, "Yo Snoop, key?", 1.0, 2.0))
    assert c.speaker.said == ["Snoop here, can't share that one."] and "ghp_" not in " ".join(printed)

def test_offline_brain():
    c, _, logs = ctx(BrainReply(False, "", 0, "offline"))
    asyncio.run(handle_utterance(c, "Yo Snoop, CI?", 1.0, 2.0))
    assert c.speaker.said == ["Snoop here, my brain's offline."] and logs[0]["outcome"] == "offline"

def test_peanut_butter_stops_speaker():
    c, _, logs = ctx(BrainReply(True, "x.", 60, None))
    asyncio.run(handle_utterance(c, "peanut butter", 1.0, 1.5))
    assert c.speaker.stopped == 1 and logs == []

def test_room_talk_is_not_logged():
    c, _, logs = ctx(BrainReply(True, "x.", 60, None))
    asyncio.run(handle_utterance(c, "we should snoop around the logs", 1.0, 2.0))
    assert logs == [] and c.brain.asked == []

def test_stop_is_heard_while_an_answer_is_being_spoken():
    c, _, _ = ctx(BrainReply(True, "One. Two. Three.", 60, None), per=0.05)
    async def go():
        t = asyncio.create_task(handle_utterance(c, "Yo Snoop, CI?", 1.0, 2.0))
        await asyncio.sleep(0.07)
        await handle_utterance(c, "peanut butter", 2.1, 2.5)
        await t
    asyncio.run(go())
    assert c.speaker.stopped == 1 and "Three." not in c.speaker.said
    assert c.log.__self__[-1]["outcome"] == "stopped"

def test_stop_while_thinking_cancels_the_answer():
    c, _, logs = ctx(BrainReply(True, "One.", 60, None), delay=0.1)
    async def go():
        t = asyncio.create_task(handle_utterance(c, "Yo Snoop, CI?", 1.0, 2.0))
        await asyncio.sleep(0.02)
        await handle_utterance(c, "peanut butter", 2.1, 2.5)
        await t
    asyncio.run(go())
    assert c.speaker.said == [] and logs[0]["outcome"] == "stopped"

def test_one_question_at_a_time():
    c, _, _ = ctx(BrainReply(True, "A.", 60, None), delay=0.05)
    async def go():
        await asyncio.gather(handle_utterance(c, "Yo Snoop, one?", 1.0, 2.0),
                             handle_utterance(c, "Yo Snoop, two?", 1.0, 2.0))
    asyncio.run(go())
    assert c.inflight_max == 1

def test_dry_mode_never_asks_the_brain():
    c, printed, logs = ctx(BrainReply(True, "x.", 60, None), dry=True)
    asyncio.run(handle_utterance(c, "Yo Snoop, CI?", 1.0, 2.0))
    asyncio.run(handle_utterance(c, "peanut butter", 3.0, 3.5))
    assert c.brain.asked == [] and logs == [] and printed == ["[dry] WAKE: CI?", "[dry] STOP"]

def test_stop_then_new_wake_still_silences_the_first_answer():
    c, _, logs = ctx(BrainReply(True, "First answer.", 60, None), delay=0.1)
    async def go():
        t1 = asyncio.create_task(handle_utterance(c, "Yo Snoop, one?", 1.0, 2.0))
        await asyncio.sleep(0.02)
        await handle_utterance(c, "peanut butter", 2.1, 2.5)
        t2 = asyncio.create_task(handle_utterance(c, "Yo Snoop, two?", 5.0, 6.0))
        await t1; await t2
    asyncio.run(go())
    assert logs[0]["outcome"] == "stopped" and logs[1]["outcome"] == "spoken"
    assert c.speaker.said.count("First answer.") == 1

def test_key_rejoined_by_markdown_removal_is_blocked():
    c, printed, _ = ctx(BrainReply(True, "Here: gh**p_" + "Q" * 36 + "**", 60, None))
    asyncio.run(handle_utterance(c, "Yo Snoop, key?", 1.0, 2.0))
    assert c.speaker.said == ["Snoop here, can't share that one."] and printed == []


def test_vosk_debug_line_shows_its_verdict():
    from yosnoop.desk.run import vosk_debug_line
    assert vosk_debug_line(True, "yo(1.00) snoop(0.98)") == "[debug] vosk: WAKE  (yo(1.00) snoop(0.98))"
    assert vosk_debug_line(False, "yo(1.00) snoop(0.98)") == "[debug] vosk: no    (yo(1.00) snoop(0.98))"


def test_vosk_wake_reaches_the_state_machine():
    out = []
    ctx = DeskCtx(state=DeskState(), brain=None, speaker=None, host_name="Brett Evans", log=lambda e: None,
                  print_fn=out.append, dry=True)
    asyncio.run(handle_utterance(ctx, "Your Snoop is the build passing", 1.0, 2.0, heard_wake=True))
    assert out == ["[dry] WAKE: is the build passing"]


def test_acknowledges_right_away_while_the_brain_thinks():
    c, _, _ = ctx(BrainReply(True, "One.", 60, None), delay=0.05, acks=("Hold up.", "One sec."))
    import time
    later = time.monotonic() + 100  # past the self-voice hold-off, which runs on the real clock
    asyncio.run(handle_utterance(c, "Yo Snoop, CI?", 1.0, 2.0))
    asyncio.run(handle_utterance(c, "Yo Snoop, PRs?", later, later + 1))
    assert c.speaker.said == ["Hold up.", "Snoop here.", "One.", "One sec.", "Snoop here.", "One."]


def test_brain_is_asked_before_the_acknowledgement_finishes():
    c, _, _ = ctx(BrainReply(True, "One.", 60, None), per=0.05, acks=("Hold up.",))
    async def go():
        t = asyncio.create_task(handle_utterance(c, "Yo Snoop, CI?", 1.0, 2.0))
        await asyncio.sleep(0.02)
        assert c.speaker.said == ["Hold up."] and c.brain.asked == [("CI?", "Brett Evans", "desk")]
        await t
    asyncio.run(go())


def test_stop_during_acknowledgement_cancels_the_answer():
    c, _, logs = ctx(BrainReply(True, "One.", 60, None), delay=0.1, per=0.05, acks=("Hold up.",))
    async def go():
        t = asyncio.create_task(handle_utterance(c, "Yo Snoop, CI?", 1.0, 2.0))
        await asyncio.sleep(0.02)
        await handle_utterance(c, "peanut butter", 2.1, 2.5)
        await t
    asyncio.run(go())
    assert c.speaker.said == ["Hold up."] and logs[0]["outcome"] == "stopped"


def test_default_acknowledgements_are_short_and_never_the_stop_phrase():
    from yosnoop.desk.run import ACKS
    assert len(ACKS) >= 3 and all(len(a.split()) <= 8 and "peanut" not in a.lower() for a in ACKS)


TIERED = "Five merged. None passed. Newest is 712.\nSUMMARY:\nSum one. Sum two.\nDETAILS:\nDet one. Det two. Det three."


def _later():
    import time
    return time.monotonic() + 100  # past the self-voice hold-off, which runs on the real clock


def test_the_rest_speaks_the_summary_without_asking_the_brain_again():
    c, _, logs = ctx(BrainReply(True, TIERED, 60, None))
    asyncio.run(handle_utterance(c, "Yo Snoop, what merged?", 1.0, 2.0))
    t = _later()
    asyncio.run(handle_utterance(c, "Yo Snoop, give me the rest", t, t + 1))
    assert c.speaker.said[-2:] == ["Sum one.", "Sum two."] and len(c.brain.asked) == 1
    assert logs[-1]["outcome"] == "spoken" and logs[-1]["question"] == "give me the rest"


def test_full_details_speaks_everything():
    c, _, _ = ctx(BrainReply(True, TIERED, 60, None))
    asyncio.run(handle_utterance(c, "Yo Snoop, what merged?", 1.0, 2.0))
    t = _later()
    asyncio.run(handle_utterance(c, "Yo Snoop, full details please", t, t + 1))
    assert c.speaker.said[-3:] == ["Det one.", "Det two.", "Det three."] and len(c.brain.asked) == 1


def test_follow_up_phrases():
    from yosnoop.desk.run import follow_up
    for q in ("give me the rest", "the rest", "tell me more", "keep going", "what else?", "Can you give me the rest of it?"):
        assert follow_up(q) == "summary", q
    for q in ("full details", "give me the full details", "all of it", "the whole answer", "tell me everything"):
        assert follow_up(q) == "details", q
    for q in ("summarize what changed in the engineer skill this week", "is CI green", "how many more PRs are open on main"):
        assert follow_up(q) is None, q


def test_follow_up_before_any_answer_goes_to_the_brain():
    c, _, _ = ctx(BrainReply(True, "Nothing yet.", 60, None))
    asyncio.run(handle_utterance(c, "Yo Snoop, tell me more", 1.0, 2.0))
    assert c.brain.asked == [("tell me more", "Brett Evans", "desk")]


def test_thinking_sounds_play_until_the_answer_is_ready():
    c, _, _ = ctx(BrainReply(True, "One.", 60, None), delay=0.3, acks=("Hold up.",), think_gap=(0.05, 0.05))
    asyncio.run(handle_utterance(c, "Yo Snoop, CI?", 1.0, 2.0))
    said = c.speaker.said
    assert said[0] == "Hold up." and said[-2:] == ["Snoop here.", "One."]
    assert len([x for x in said[1:-2] if x == "<rustle>" or x in ("Hmm.", "Mm, okay.", "Let's see.")]) >= 3


def test_default_thinking_gap_is_a_few_seconds():
    from yosnoop.desk.run import DeskCtx as D
    from yosnoop.desk.thinking import GAP_S
    assert D(None, None, None, "x", print).think_gap == GAP_S == (3.0, 5.0)
