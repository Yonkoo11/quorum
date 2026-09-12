// UI launch clip for X: the new runquorum.site, 2026-09-12. Silent. Every clip is the live site, driven by a browser.
// Durations come from ffprobe on the recordings in public/video (30 fps): Math.round(seconds * 30).
export const UI_FPS = 30;
export const UI_W = 1920;
export const UI_H = 1080;
export const UI_CROSSFADE = 15;

// The site's own tokens (docs/quorum.css), not the skill's archetype theme. See DECISIONS.md.
export const UI_COLORS = {
  paper: "#f3eee4",
  surface: "#f9f6ee",
  ink: "#121212",
  green: "#3fb950",
  greenText: "#24772f",
  muted: "#6f6a5e",
};

export type UiScene =
  | { key: string; kind: "title"; frames: number; label: string; lines: string[] }
  | { key: string; kind: "clip"; frames: number; label: string; file: string }
  | { key: string; kind: "phone"; frames: number; label: string; file: string }
  | { key: string; kind: "close"; frames: number; label: string; still: string; lines: string[] };

export const UI_SCENES: readonly UiScene[] = [
  { key: "title", kind: "title", frames: 75, label: "OPEN SOURCE · MIT", lines: ["The new", "runquorum.site."] },
  { key: "front", kind: "clip", frames: 204, label: "THE DELETION TEST", file: "video/ui-front.mp4" }, // 6.80 s
  { key: "board", kind: "clip", frames: 162, label: "ONE PAGE, ONE PROOF", file: "video/ui-board.mp4" }, // 5.40 s
  { key: "registry", kind: "clip", frames: 268, label: "VERIFIED IN YOUR BROWSER", file: "video/ui-registry.mp4" }, // 8.93 s
  { key: "dark", kind: "clip", frames: 140, label: "LIGHT AND DARK", file: "video/ui-dark.mp4" }, // 4.67 s
  { key: "phone", kind: "phone", frames: 170, label: "ON A PHONE", file: "video/ui-phone.mp4" }, // 5.67 s
  { key: "close", kind: "close", frames: 120, label: "THE INTERSECTION IS THE FINDING.", still: "video/ui-close.png", lines: ["runquorum.site"] },
];

export const UI_TOTAL_FRAMES =
  UI_SCENES.reduce((a, s) => a + s.frames, 0) - UI_CROSSFADE * (UI_SCENES.length - 1);
