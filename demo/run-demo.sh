#!/bin/zsh
# Continuous, unedited Quorum session. Every command really runs.
# Beat start times are logged so narration can be aligned without cutting the video.
cd /Users/yonko/Projects/quorum || exit 1
export PATH="/Users/yonko/Projects/quorum/.venv/bin:$PATH"
BEATS=/private/tmp/claude-501/-Users-yonko/76182d1a-b65b-464d-bfe0-728904884f6e/scratchpad/demo/beats.tsv
: > "$BEATS"
clear
rm -f quorum-memory.db

GREEN=$'\033[32m'; CYAN=$'\033[36m'; DIM=$'\033[2m'; RESET=$'\033[0m'; BOLD=$'\033[1m'
T0=$(python3 -c 'import time;print(time.time())')
now() { python3 -c 'import time;print(time.time())'; }
elapsed() { python3 -c "print(round($(now)-$T0,3))"; }

beat() {          # beat <key> <command> <target_seconds>
  local key="$1" cmd="$2" target="$3"
  printf "%s\t%s\n" "$key" "$(elapsed)" >> "$BEATS"
  local start=$(now)
  printf "%s➜%s  %s" "$GREEN" "$RESET" "$CYAN"
  for (( i=1; i<=${#cmd}; i++ )); do printf "%s" "${cmd:$((i-1)):1}"; sleep 0.02; done
  printf "%s\n" "$RESET"
  sleep 0.4
  eval "$cmd"
  echo
  python3 -c "
import time
rest = $target - (time.time() - $start)
time.sleep(max(rest, 0.8))"
}

sleep 1.5
printf "%s%s  Quorum — one continuous session, nothing cut%s\n\n" "$BOLD" "$DIM" "$RESET"
sleep 3.5

beat b1 'date -u && git rev-parse --short HEAD'                 7
beat b2 'quorum recall'                                          6
beat b3 'quorum run --targets fixtures/*.sol'                   16
beat b4 'quorum swarm --workers 3'                              16
beat b5 'quorum recall'                                         17
beat b6 'quorum run --no-memory'                                11
beat b7 'quorum verify 0xa648821d91093df770b72c60be56834d069c9355c785e6195183e911f00bf713' 12

printf "%s\t%s\n" "end" "$(elapsed)" >> "$BEATS"
printf "%s%s  six agents · no message bus · memory is the coordination layer%s\n" "$DIM" "$BOLD" "$RESET"
sleep 3
