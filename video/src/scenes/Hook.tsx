import React from "react";
import { AbsoluteFill, Sequence, interpolate, useCurrentFrame } from "remotion";
import { AnimatedBackground } from "../components/AnimatedBackground";
import { GlowText } from "../components/GlowText";
import { Lens } from "../components/Lens";
import { COLORS } from "../constants";
import { MONO } from "../fonts";

const NAMES = ["callorder", "guard", "modifier", "sender", "unchecked", "precision"];

export const Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const fade = interpolate(frame, [0, 14], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      <AnimatedBackground />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", opacity: fade }}>
        <GlowText text="quorum" fontSize={148} color={COLORS.accent} fontFamily={MONO} fontWeight={700} />
        <GlowText
          text="six agents, one memory, no messages between them"
          fontSize={40} color={COLORS.white} fontWeight={500} delay={16}
          style={{ marginTop: 24, letterSpacing: 0.3 }}
        />
      </AbsoluteFill>
      <Sequence from={34}>
        <AbsoluteFill>
          {NAMES.map((n, i) => (
            <Lens key={n} label={n} delay={i * 4} state="idle" x={92 + (i % 3) * 560} y={i < 3 ? 118 : 862} />
          ))}
        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};
