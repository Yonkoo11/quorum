// Pitch video — GAP mode (Brian edge-tts, raw 1.0x; VTT sentence timings are exact).
// Founder pitch, distinct from the demo. Reuses the Quorum theme from ../constants.
import { COLORS, PROOFS } from "../constants";

export { COLORS };
export const FPS = 30;
export const W = 1920;
export const H = 1080;
export const PLAYBACK_RATE = 1.0;

export const SCENE_ORDER = ["problem", "solution", "traction", "moat", "closeask"] as const;
export type PScene = (typeof SCENE_ORDER)[number];

// From afinfo on public/audio/pitch/*.mp3 (round(sec*30)).
export const AUDIO_DURATIONS: Record<PScene, number> = {
  problem: 314,
  solution: 304,
  traction: 575,
  moat: 481,
  closeask: 608,
};

export const SCENE_GAP = 30; // 1.0s (raw Brian already paces slow)

export const SCENE_DURATIONS: Record<PScene, number> = {
  problem: AUDIO_DURATIONS.problem + SCENE_GAP,
  solution: AUDIO_DURATIONS.solution + SCENE_GAP,
  traction: AUDIO_DURATIONS.traction + SCENE_GAP,
  moat: AUDIO_DURATIONS.moat + SCENE_GAP,
  closeask: AUDIO_DURATIONS.closeask + SCENE_GAP,
};

export const CROSSFADE = 15;
export const TOTAL_FRAMES =
  Object.values(SCENE_DURATIONS).reduce((a, b) => a + b, 0) - CROSSFADE * (SCENE_ORDER.length - 1);

export const AUDIO_FILES: Record<PScene, string> = {
  problem: "audio/pitch/problem.mp3",
  solution: "audio/pitch/solution.mp3",
  traction: "audio/pitch/traction.mp3",
  moat: "audio/pitch/moat.mp3",
  closeask: "audio/pitch/closeask.mp3",
};

// Subtitle timings: edge-tts VTT sentence cues (exact). Display text is clean/written.
type Sub = { text: string; start: number; end: number };
export const SUBTITLES: Record<PScene, Sub[]> = {
  problem: [
    { text: "Every week, a report says a smart contract has a critical bug.", start: 2, end: 130 },
    { text: "Usually, no one can tell if it's real.", start: 130, end: 210 },
    { text: "A finding is just a claim until someone runs it.", start: 210, end: 314 },
  ],
  solution: [
    { text: "Quorum only publishes a bug it can prove.", start: 2, end: 92 },
    { text: "It writes the exploit, runs it on a mainnet fork, and keeps it only if the attacker's balance goes up.", start: 92, end: 304 },
  ],
  traction: [
    { text: "It drained four real 2026 hacks to the wei, one with the answer withheld from the model.", start: 2, end: 181 },
    { text: "A cross-chain bridge confirmed a latent defect Quorum flagged on Robinhood Chain. Fix scheduled.", start: 181, end: 362 },
    { text: "It publishes its own miss rate: 64% recall, and the one row where Slither still wins.", start: 362, end: 575 },
  ],
  moat: [
    { text: "Three things are new: disclosure gated on a running exploit, a tool that publishes how often it's wrong, and a proof that settles on-chain.", start: 2, end: 280 },
    { text: "Each proof burns a fee and records its digest in one transaction, so a record carries its own cost.", start: 280, end: 481 },
  ],
  closeask: [
    { text: "Built for protocol teams shipping money on Arbitrum and Robinhood Chain, and the researchers who disclose to them.", start: 2, end: 207 },
    { text: "Live on both chains today.", start: 207, end: 270 },
    { text: "Next, it hunts and proves across every verified Arbitrum contract holding real money. If nothing proves, it says so.", start: 270, end: 505 },
    { text: "Prove it, or drop it.", start: 505, end: 554 },
    { text: "runquorum.site", start: 554, end: 608 },
  ],
};

// ===== content (real, verified) =====
export { PROOFS };

export const PROBLEM_STAMP = "UNPROVEN";
export const PROBLEM_REPORT = { label: "SECURITY FINDING", severity: "CRITICAL?", body: "high impact, drains the vault" };
export const PROBLEM_HEADLINE = "A finding is just a claim until someone runs it.";

export const SOLUTION_TITLE = "Quorum only ships what it can prove.";
export const SOLUTION_STEPS = [
  { k: "01", t: "Write the exploit" },
  { k: "02", t: "Run it on a mainnet fork" },
  { k: "03", t: "Keep it only if the balance goes up" },
];

export const TRACTION_ROWS = [
  { head: "Proven by execution", body: "Four real 2026 hacks drained to the wei, one fully blind" },
  { head: "A team agreed", body: "A cross-chain bridge confirmed a latent defect, fix scheduled" },
  { head: "Honest about misses", body: "64% recall, published, including the row Slither still wins" },
];

export const MOAT_CARDS = [
  { t: "Disclosure gated on a running exploit", s: "publish only what drains on a fork" },
  { t: "Publishes its own miss rate", s: "the hits and the misses, on the page" },
  { t: "Each proof settles on-chain", s: "fee burned + digest, one transaction" },
];

export const CLOSE = {
  market: "For protocol teams shipping money on Arbitrum and Robinhood Chain, and the researchers who disclose to them.",
  chains: "Live on Robinhood Chain and Arbitrum One",
  roadmap: "Next: hunt and prove across every verified Arbitrum contract holding real money. If nothing proves, we say so.",
  tagline: "Prove it. Or drop it.",
  url: "runquorum.site",
  event: "Arbitrum Open House · Singapore",
};
