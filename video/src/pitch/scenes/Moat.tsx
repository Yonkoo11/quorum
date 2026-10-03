import React from "react";
import { AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { AnimatedBackground } from "../../components/AnimatedBackground";
import { GlowText } from "../../components/GlowText";
import { COLORS, MOAT_CARDS } from "../constants";
import { INTER, MONO } from "../../fonts";

const Card: React.FC<{ n: number; t: string; s: string; delay: number }> = ({ n, t, s, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const sp = spring({ frame: frame - delay, fps, config: { damping: 18, stiffness: 90 } });
  return (
    <div
      style={{
        opacity: sp,
        transform: `translateY(${interpolate(sp, [0, 1], [24, 0])}px)`,
        width: 380,
        height: 300,
        background: COLORS.bgCardStrong,
        border: `1px solid ${COLORS.border}`,
        borderRadius: 18,
        padding: "34px 30px",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div style={{ fontFamily: MONO, fontSize: 40, fontWeight: 700, color: COLORS.accent }}>{`0${n}`}</div>
      <div style={{ fontFamily: INTER, fontSize: 30, fontWeight: 700, color: COLORS.white, marginTop: 20, lineHeight: 1.25 }}>
        {t}
      </div>
      <div style={{ flex: 1 }} />
      <div style={{ fontFamily: INTER, fontSize: 21, color: COLORS.offWhite, lineHeight: 1.35 }}>{s}</div>
    </div>
  );
};

export const Moat: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      <AnimatedBackground />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <GlowText text="Three things are new, together." fontSize={50} color={COLORS.white} fontWeight={800} style={{ marginBottom: 48 }} />
        <div style={{ display: "flex", gap: 28 }}>
          {MOAT_CARDS.map((c, i) => (
            <Card key={c.t} n={i + 1} t={c.t} s={c.s} delay={18 + i * 12} />
          ))}
        </div>
        <Sequence from={280} layout="none">
          <GlowText
            text="A record cannot exist without paying for itself."
            fontSize={30}
            color={COLORS.accentBright}
            fontWeight={600}
            fontFamily={MONO}
            style={{ marginTop: 44 }}
          />
        </Sequence>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
