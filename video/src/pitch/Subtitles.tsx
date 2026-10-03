import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { INTER } from "../fonts";
import { CROSSFADE, SCENE_DURATIONS, SCENE_ORDER, SUBTITLES } from "./constants";

type G = { text: string; s: number; e: number };
function build(): G[] {
  const out: G[] = [];
  let off = 0;
  SCENE_ORDER.forEach((k, i) => {
    for (const s of SUBTITLES[k]) out.push({ text: s.text, s: off + s.start, e: off + s.end });
    off += SCENE_DURATIONS[k] - (i < SCENE_ORDER.length - 1 ? CROSSFADE : 0);
  });
  return out;
}
const E = build();

export const PitchSubtitles: React.FC = () => {
  const frame = useCurrentFrame();
  const a = E.find((x) => frame >= x.s && frame < x.e);
  if (!a) return null;
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", zIndex: 50 }}>
      <div style={{ background: "rgba(0,0,0,0.74)", borderRadius: 10, padding: "12px 30px", marginBottom: 46, maxWidth: 1560 }}>
        <div style={{ fontFamily: INTER, fontSize: 36, fontWeight: 600, color: "#ffffff", textAlign: "center", lineHeight: 1.4 }}>
          {a.text}
        </div>
      </div>
    </AbsoluteFill>
  );
};
