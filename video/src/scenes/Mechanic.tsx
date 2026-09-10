import React from "react";
import { AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { AnimatedBackground } from "../components/AnimatedBackground";
import { GlowText } from "../components/GlowText";
import { COLORS } from "../constants";
import { INTER, MONO } from "../fonts";

const TIERS = [
  { tier: "HOT", dir: "state/", role: "who is scanning what" },
  { tier: "WARM", dir: "entities/", role: "which lenses corroborated" },
  { tier: "COLD", dir: "journal/", role: "every sighting, appended" },
  { tier: "REFERENCE", dir: "reference/", role: "idioms confirmed for good" },
  { tier: "ARCHIVE", dir: "archive/", role: "what a human retired" },
];

const TierRow: React.FC<{ i: number; tier: string; dir: string; role: string }> = ({ i, tier, dir, role }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const prog = spring({ frame: frame - 30 - i * 9, fps, config: { damping: 17, stiffness: 100 } });
  const op = interpolate(prog, [0, 0.4], [0, 1], { extrapolateRight: "clamp" });
  const x = interpolate(prog, [0, 1], [-26, 0]);
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 26, opacity: op, transform: `translateX(${x}px)`,
      background: COLORS.bgCard, border: `1px solid ${COLORS.border}`, borderRadius: 12,
      padding: "16px 26px", width: 1180, marginBottom: 12,
    }}>
      <div style={{ fontFamily: MONO, fontSize: 22, color: COLORS.accent, width: 148 }}>{tier}</div>
      <div style={{ fontFamily: MONO, fontSize: 22, color: COLORS.offWhite, width: 190 }}>{dir}</div>
      <div style={{ fontFamily: INTER, fontSize: 26, color: COLORS.white }}>{role}</div>
    </div>
  );
};

export const Mechanic: React.FC = () => {
  const frame = useCurrentFrame();
  const ruleOp = interpolate(frame, [300, 320], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      <AnimatedBackground />
      <AbsoluteFill style={{ alignItems: "center", paddingTop: 74 }}>
        <GlowText text="one shared memory, five tiers" fontSize={56} color={COLORS.white} fontWeight={700} />
        <div style={{ marginTop: 34 }}>
          {TIERS.map((t, i) => <TierRow key={t.tier} i={i} {...t} />)}
        </div>
      </AbsoluteFill>
      <Sequence from={296}>
        <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 152 }}>
          <div style={{
            opacity: ruleOp, fontFamily: INTER, fontSize: 38, fontWeight: 700, color: COLORS.accentBright,
            background: COLORS.bgCardStrong, border: `1px solid ${COLORS.borderStrong}`,
            borderRadius: 14, padding: "18px 38px",
          }}>
            two lenses, different evidence, same conclusion = published
          </div>
        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};
