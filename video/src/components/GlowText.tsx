import React from "react";
import { useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { INTER } from "../fonts";

export const GlowText: React.FC<{
  text: string; fontSize: number; color: string; delay?: number;
  fontWeight?: number; fontFamily?: string; glowIntensity?: number;
  style?: React.CSSProperties;
}> = ({ text, fontSize, color, delay = 0, fontWeight = 800, fontFamily, glowIntensity = 1, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const prog = spring({ frame: frame - delay, fps, config: { mass: 1, damping: 15, stiffness: 80 } });
  const opacity = interpolate(prog, [0, 0.4], [0, 1], { extrapolateRight: "clamp" });
  const y = interpolate(prog, [0, 1], [20, 0]);
  return (
    <div style={{
      fontFamily: fontFamily ?? INTER, fontSize, fontWeight, color,
      opacity, transform: `translateY(${y}px)`,
      textShadow: `0 0 ${20 * glowIntensity}px ${color}60, 0 0 ${60 * glowIntensity}px ${color}30`,
      ...style,
    }}>{text}</div>
  );
};
