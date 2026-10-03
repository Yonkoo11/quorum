import React from "react";
import { AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { AnimatedBackground } from "../../components/AnimatedBackground";
import { GlowText } from "../../components/GlowText";
import { COLORS, PROOFS } from "../constants";
import { INTER, MONO } from "../../fonts";

const Chip: React.FC<{ name: string; amount: string; delay: number }> = ({ name, amount, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 16, stiffness: 90 } });
  return (
    <div
      style={{
        opacity: s,
        transform: `translateY(${interpolate(s, [0, 1], [18, 0])}px)`,
        background: COLORS.bgCardStrong,
        border: `1px solid ${COLORS.border}`,
        borderRadius: 14,
        padding: "16px 20px",
        textAlign: "center",
        minWidth: 250,
      }}
    >
      <div style={{ fontFamily: MONO, fontSize: 28, fontWeight: 700, color: COLORS.accentBright }}>{amount}</div>
      <div style={{ fontFamily: INTER, fontSize: 20, fontWeight: 600, color: COLORS.white, marginTop: 4 }}>{name}</div>
    </div>
  );
};

const Row: React.FC<{ head: string; body: string; delay: number }> = ({ head, body, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 18, stiffness: 90 } });
  return (
    <div
      style={{
        opacity: s,
        transform: `translateX(${interpolate(s, [0, 1], [-24, 0])}px)`,
        display: "flex",
        alignItems: "baseline",
        gap: 18,
        width: 1120,
        background: COLORS.bgCard,
        border: `1px solid ${COLORS.border}`,
        borderRadius: 14,
        padding: "18px 30px",
      }}
    >
      <div style={{ fontFamily: INTER, fontSize: 24, fontWeight: 700, color: COLORS.accent, minWidth: 250 }}>{head}</div>
      <div style={{ fontFamily: INTER, fontSize: 24, color: COLORS.white }}>{body}</div>
    </div>
  );
};

export const Traction: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      <AnimatedBackground />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <GlowText text="Traction" fontSize={52} color={COLORS.white} fontWeight={800} style={{ marginBottom: 14 }} />
        <GlowText
          text="Four real 2026 hacks, drained on a fork to the wei"
          fontSize={26}
          color={COLORS.offWhite}
          fontWeight={500}
          delay={10}
          style={{ marginBottom: 30 }}
        />
        <div style={{ display: "flex", gap: 20, marginBottom: 34 }}>
          {PROOFS.map((p, i) => (
            <Chip key={p.name} name={p.name} amount={p.amount} delay={20 + i * 6} />
          ))}
        </div>
        <Sequence from={181} layout="none">
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Row head="A team agreed" body="A cross-chain bridge confirmed a latent defect, fix scheduled" delay={0} />
            <Row head="Honest about misses" body="64% recall, published, including the row Slither still wins" delay={10} />
          </div>
        </Sequence>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
