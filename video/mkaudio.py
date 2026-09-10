"""Generate one audio file per spoken sentence, then emit timing.json.

One file per sentence means the caption text is byte identical to the audio and
the timing comes from ffprobe rather than a transcription guess.
"""
import json, subprocess
from pathlib import Path

VOICE = "en-US-AndrewMultilingualNeural"
FPS = 30
HERE = Path(__file__).parent
OUT = HERE / "public" / "audio"
OUT.mkdir(parents=True, exist_ok=True)

# Terminal scene: sentences are pinned to the second the on-screen event happens.
TERM_ANCHORS = {
    "t0": 1.0, "t1": 5.0, "t2": 8.6, "t3": 13.0,
    "t4": 23.4, "t5": 29.0, "t6": 40.3, "t7": 46.0, "t8": 51.0,
    "t9": 59.4, "t10": 63.4, "t11": 70.6,
}

SCRIPT = {
 "hook": [
   "Six agents. One memory. No messages between them.",
 ],
 "problem": [
   "Run six code review agents and you get six opinions and no agreement.",
   "Each one re-finds what it found last week.",
   "Each one re-reports the thing you already threw away.",
   "And they all scan the same file, because none of them knows what the others are doing.",
 ],
 "mechanic": [
   "Quorum gives them one shared memory and takes away everything else.",
   "A finding is only published when two lenses reach it from different evidence.",
   "Whoever agreed is counted in memory, not in any agent's head.",
 ],
 "terminal": {
   "t0": "Timestamp and commit hash, so you know none of this is pre-baked.",
   "t1": "Empty memory. The swarm knows nothing.",
   "t2": "Six lenses read two known-vulnerable contracts.",
   "t3": "Two findings published, five held back because only one lens believed them.",
   "t4": "Now three separate processes, sharing that memory and nothing else.",
   "t5": "Twenty-four units of work, each done exactly once, because every agent claimed its work in memory first.",
   "t6": "These are real contracts pulled from Base mainnet, which this swarm has never read.",
   "t7": "The reentrancy idiom was confirmed on a fixture by two lenses.",
   "t8": "It is now recognised inside Friend Tech's live contract from a single sighting, because the swarm already paid for that knowledge.",
   "t9": "Same swarm, same contracts, memory removed.",
   "t10": "Nothing is confirmed. Nothing is recalled. It falls apart.",
   "t11": "And the claim published on Base: the digest recomputed from memory matches the chain.",
 },
 "close": [
   "Memory is the coordination layer.",
   "Take it away and there is no swarm left.",
 ],
}


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "default=noprint_wrappers=1:nokey=1", str(p)],
                                capture_output=True, text=True).stdout.strip())


def say(key, text):
    f = OUT / f"{key}.mp3"
    if not f.exists():
        subprocess.run(["edge-tts", "--voice", VOICE, "--rate=+4%", "--text", text,
                        "--write-media", str(f)], check=True, capture_output=True)
    return {"text": text, "file": f"audio/{key}.mp3", "dur": dur(f)}


timing = {}
for scene in ("hook", "problem", "mechanic", "close"):
    items, t = [], 0.6
    for i, text in enumerate(SCRIPT[scene]):
        it = say(f"{scene}_{i}", text)
        items.append({**it, "start": round(t, 3)})
        t += it["dur"] + 0.22
    tail = {"hook": 2.6, "problem": 1.0, "mechanic": 1.2, "close": 2.4}[scene]
    timing[scene] = {"items": items, "seconds": round(t + tail, 3)}

term = []
for key, text in SCRIPT["terminal"].items():
    it = say(key, text)
    term.append({**it, "start": TERM_ANCHORS[key]})
timing["terminal"] = {"items": term, "seconds": 78.4}

(HERE / "src" / "timing.json").write_text(json.dumps(timing, indent=2))
for k, v in timing.items():
    print(f"{k:9} {v['seconds']:6.2f}s  ({len(v['items'])} lines)")
overlaps = [(a["text"][:40], round(a["start"] + a["dur"], 2), b["start"])
            for a, b in zip(term, term[1:]) if a["start"] + a["dur"] > b["start"] - 0.15]
for o in overlaps:
    print("  OVERLAP", o)
if not overlaps:
    print("  terminal narration lines do not overlap")
