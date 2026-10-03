import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { AnimatedBackground } from "../../components/AnimatedBackground";
import { GlowText } from "../../components/GlowText";
import { COLORS, SOLUTION_STEPS, SOLUTION_TITLE } from "../constants";
import { INTER, MONO } from "../../fonts";

const Step: React.FC<{ k: string; t: string; delay: number; last: boolean }> = ({ k, t, delay, last }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 18, stiffness: 90 } });
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
      <div
        style={{
          opacity: s,
          transform: `translateY(${interpolate(s, [0, 1], [20, 0])}px)`,
          width: 320,
          background: COLORS.bgCardStrong,
          border: `1px solid ${COLORS.border}`,
          borderRadius: 16,
          padding: "26px 24px",
          textAlign: "center",
        }}
      >
        <div style={{ fontFamily: MONO, fontSize: 22, color: COLORS.accent, fontWeight: 700 }}>{k}</div>
        <div style={{ fontFamily: INTER, fontSize: 25, fontWeight: 600, color: COLORS.white, marginTop: 12, lineHeight: 1.3 }}>
          {t}
        </div>
      </div>
      {!last && (
        <div style={{ opacity: s, fontFamily: MONO, fontSize: 40, color: COLORS.accentDim }}>{"→"}</div>
      )}
    </div>
  );
};

export const Solution: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      <AnimatedBackground />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <GlowText text={SOLUTION_TITLE} fontSize={54} color={COLORS.white} fontWeight={800} style={{ marginBottom: 56, textAlign: "center" }} />
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          {SOLUTION_STEPS.map((st, i) => (
            <Step key={st.k} k={st.k} t={st.t} delay={20 + i * 16} last={i === SOLUTION_STEPS.length - 1} />
          ))}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
