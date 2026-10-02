import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { INTER } from "./fonts";
import { CROSSFADE, SCENE_DURATIONS, SCENE_ORDER, SUBTITLES } from "./constants";

type GlobalEntry = { text: string; startFrame: number; endFrame: number };

function build(): GlobalEntry[] {
  const entries: GlobalEntry[] = [];
  let offset = 0;
  SCENE_ORDER.forEach((key, i) => {
    for (const s of SUBTITLES[key]) {
      entries.push({ text: s.text, startFrame: offset + s.start, endFrame: offset + s.end });
    }
    offset += SCENE_DURATIONS[key] - (i < SCENE_ORDER.length - 1 ? CROSSFADE : 0);
  });
  return entries;
}

const ENTRIES = build();

export const Subtitles: React.FC = () => {
  const frame = useCurrentFrame();
  const active = ENTRIES.find((e) => frame >= e.startFrame && frame < e.endFrame);
  if (!active) return null;
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", zIndex: 50 }}>
      <div
        style={{
          background: "rgba(0,0,0,0.74)",
          borderRadius: 10,
          padding: "12px 30px",
          marginBottom: 46,
          maxWidth: 1560,
        }}
      >
        <div
          style={{
            fontFamily: INTER,
            fontSize: 36,
            fontWeight: 600,
            color: "#ffffff",
            textAlign: "center",
            lineHeight: 1.4,
          }}
        >
          {active.text}
        </div>
      </div>
    </AbsoluteFill>
  );
};
