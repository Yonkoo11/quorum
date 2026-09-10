import timing from "./timing.json";

export const FPS = 30;
export const W = 1920;
export const H = 1080;
export const CROSSFADE = 15;

export const COLORS = {
  bg: "#080c09",
  bgCard: "rgba(15,30,18,0.62)",
  bgCardStrong: "rgba(12,24,15,0.9)",
  accent: "#3fb950",
  accentDim: "#166534",
  accentBright: "#5ddb70",
  white: "#eef5ef",
  offWhite: "#a8b8ac",
  muted: "#5a6e5e",
  border: "rgba(63,185,80,0.22)",
  borderStrong: "rgba(63,185,80,0.4)",
  red: "#f85149",
  amber: "#d29922",
  cyan: "#22d3ee",
  terminalBg: "#121314",
};

export const ORBS = [
  { baseX: 250, baseY: 210, size: 480, color: COLORS.accent, blur: 120, opacity: 0.12, speed: 0.006 },
  { baseX: 1560, baseY: 780, size: 420, color: COLORS.accentDim, blur: 110, opacity: 0.11, speed: 0.005 },
  { baseX: 960, baseY: 520, size: 560, color: "#0e7490", blur: 140, opacity: 0.08, speed: 0.008 },
  { baseX: 1690, baseY: 170, size: 380, color: COLORS.cyan, blur: 100, opacity: 0.06, speed: 0.007 },
  { baseX: 180, baseY: 840, size: 320, color: COLORS.accent, blur: 100, opacity: 0.06, speed: 0.009 },
];

const sec = (s: number) => Math.round(s * FPS);

export const SCENE_ORDER = ["hook", "problem", "mechanic", "terminal", "close"] as const;
export type SceneKey = (typeof SCENE_ORDER)[number];

export const SCENE_DURATIONS: Record<SceneKey, number> = {
  hook: sec(timing.hook.seconds),
  problem: sec(timing.problem.seconds),
  mechanic: sec(timing.mechanic.seconds),
  terminal: sec(timing.terminal.seconds),
  close: sec(timing.close.seconds),
};

export const TOTAL_FRAMES =
  Object.values(SCENE_DURATIONS).reduce((a, b) => a + b, 0) - CROSSFADE * (SCENE_ORDER.length - 1);

export const TIMING = timing as Record<
  SceneKey,
  { seconds: number; items: { text: string; file: string; dur: number; start: number }[] }
>;

// The recorded session, in frames of the source file. agg renders the 91.7s cast
// slightly slower than real time, so k maps session seconds onto video frames.
const K = 1.0339;
const at = (sessionSeconds: number) => Math.round(sessionSeconds * K * FPS);

export const TERMINAL_PARTS = [
  // setup: sped up, nothing load-bearing happens here
  { from: 0, to: at(34.9), rate: 1.6, chapter: "the swarm agrees" },
  // UNCUT: three processes, cross-session recall, and the ablation, at real speed
  { from: at(34.9), to: at(79.56 + 2.0), rate: 1.0, chapter: "one memory, three processes" },
  // the on-chain claim
  { from: at(79.56 + 2.0), to: at(91.73), rate: 1.3, chapter: "the claim on Base" },
];
