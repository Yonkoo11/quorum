import React from "react";
import { useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { COLORS } from "../constants";
import { MONO } from "../fonts";

/** One agent, drawn as a node. Agreement is shown by colour, never by a line between agents. */
export const Lens: React.FC<{
  label: string; x: number; y: number; delay: number;
  state?: "idle" | "agree" | "alone"; pulse?: boolean;
}> = ({ label, x, y, delay, state = "idle", pulse = false }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const prog = spring({ frame: frame - delay, fps, config: { damping: 14, stiffness: 90 } });
  const scale = interpolate(prog, [0, 1], [0.86, 1]);
  const opacity = interpolate(prog, [0, 0.35], [0, 1], { extrapolateRight: "clamp" });
  const breathe = pulse ? 1 + Math.sin((frame - delay) * 0.12) * 0.035 : 1;

  const tint = state === "agree" ? COLORS.accent : state === "alone" ? COLORS.amber : COLORS.muted;
  return (
    <div style={{
      position: "absolute", left: x, top: y, transform: `scale(${scale * breathe})`,
      opacity, width: 232, padding: "18px 20px", borderRadius: 14,
      background: COLORS.bgCardStrong, border: `1px solid ${tint}55`,
      boxShadow: state === "agree" ? `0 0 34px ${COLORS.accent}30` : "none",
      fontFamily: MONO, fontSize: 21, color: tint, textAlign: "center",
    }}>{label}</div>
  );
};
