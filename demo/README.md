# The recorded session

`demo.cast` is the asciicast of the session in the demo video. It is a real pty
recording: every command in `run-demo.sh` actually ran, and `beats.tsv` holds the
wall-clock offset of each command so narration could be aligned without cutting
the video.

Replay it in a terminal:

    asciinema play demo.cast

Or re-render it to a GIF the way the video does:

    agg demo.cast demo.gif --font-size 27 --fps-cap 30 --theme asciinema --idle-time-limit 60

`record_cast.py` produced the cast. It strips every secret-shaped variable out of
the environment before spawning the shell, so the filmed session can reach a
read-only Base RPC endpoint and nothing else.
