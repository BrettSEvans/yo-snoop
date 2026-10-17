import json, time
lines = [l.strip() for l in open("spikes/p2_script.txt") if l.strip()]
with open("/tmp/p2-marks.ndjson", "a") as out:
    for l in lines:
        input(f"SAY: {l}\n  (press Enter when you finish) ")
        out.write(json.dumps({"line": l, "end_epoch": time.time()}) + "\n")
