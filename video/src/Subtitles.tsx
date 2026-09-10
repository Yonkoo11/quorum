import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { INTER } from "./fonts";
import { CROSSFADE, FPS, SCENE_DURATIONS, SCENE_ORDER, TIMING } from "./constants";

type GlobalEntry = { text: string; startFrame: number; endFrame: number };

function build(): GlobalEntry[] {
  const entries: GlobalEntry[] = [];
  let offset = 0;
  SCENE_ORDER.forEach((key, i) => {
    for (const item of TIMING[key].items) {
      const start = offset + Math.round(item.start * FPS);
      entries.push({
        text: item.text,
        startFrame: start,
        endFrame: start + Math.round(item.dur * FPS) + 6,
      });
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
      <div style={{
        background: "rgba(0,0,0,0.74)", borderRadius: 10, padding: "12px 30px",
        marginBottom: 46, maxWidth: 1560,
      }}>
        <div style={{
          fontFamily: INTER, fontSize: 36, fontWeight: 600, color: "#ffffff",
          textAlign: "center", lineHeight: 1.4,
        }}>{active.text}</div>
      </div>
    </AbsoluteFill>
  );
};
