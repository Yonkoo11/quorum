import React from "react";
import { AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { AnimatedBackground } from "../components/AnimatedBackground";
import { GlowText } from "../components/GlowText";
import { COLORS, PROOFS } from "../constants";
import { INTER, MONO } from "../fonts";

const Chip: React.FC<{ name: string; amount: string; chain: string; delay: number }> = ({
  name,
  amount,
  chain,
  delay,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 16, stiffness: 90 } });
  const y = interpolate(s, [0, 1], [26, 0]);
  return (
    <div
      style={{
        opacity: s,
        transform: `translateY(${y}px)`,
        background: COLORS.bgCardStrong,
        border: `1px solid ${COLORS.border}`,
        borderRadius: 16,
        padding: "22px 30px",
        minWidth: 300,
        textAlign: "center",
      }}
    >
      <div style={{ fontFamily: MONO, fontSize: 34, fontWeight: 700, color: COLORS.accentBright }}>{amount}</div>
      <div style={{ fontFamily: INTER, fontSize: 25, fontWeight: 600, color: COLORS.white, marginTop: 8 }}>{name}</div>
      <div style={{ fontFamily: MONO, fontSize: 17, color: COLORS.muted, marginTop: 4 }}>{chain}</div>
    </div>
  );
};

export const Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 14], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      <AnimatedBackground />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", opacity: fadeIn }}>
        <GlowText text="Prove it." fontSize={150} color={COLORS.white} fontWeight={900} style={{ letterSpacing: -3 }} />
        <GlowText
          text="Or drop it."
          fontSize={150}
          color={COLORS.accent}
          fontWeight={900}
          fontFamily={INTER}
          delay={10}
          style={{ letterSpacing: -3, marginTop: -6 }}
        />
        <Sequence from={120} layout="none">
          <div style={{ display: "flex", gap: 26, marginTop: 64 }}>
            {PROOFS.map((p, i) => (
              <Chip key={p.name} name={p.name} amount={p.amount} chain={p.chain} delay={i * 7} />
            ))}
          </div>
        </Sequence>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
