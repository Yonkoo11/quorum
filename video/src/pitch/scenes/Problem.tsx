import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { AnimatedBackground } from "../../components/AnimatedBackground";
import { GlowText } from "../../components/GlowText";
import { COLORS, PROBLEM_HEADLINE, PROBLEM_REPORT, PROBLEM_STAMP } from "../constants";
import { INTER, MONO } from "../../fonts";

export const Problem: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const card = spring({ frame, fps, config: { damping: 200, mass: 0.7 } });
  const stamp = spring({ frame: frame - 40, fps, config: { damping: 12, stiffness: 120 } });
  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      <AnimatedBackground />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        {/* the "report" - greyed, asserting impact */}
        <div
          style={{
            position: "relative",
            opacity: card,
            transform: `translateY(${interpolate(card, [0, 1], [24, 0])}px)`,
            width: 760,
            background: "rgba(20,24,21,0.55)",
            border: "1px solid rgba(90,110,94,0.3)",
            borderRadius: 18,
            padding: "34px 40px",
          }}
        >
          <div style={{ fontFamily: MONO, fontSize: 19, letterSpacing: 2, color: COLORS.muted }}>
            {PROBLEM_REPORT.label}
          </div>
          <div style={{ fontFamily: INTER, fontSize: 56, fontWeight: 800, color: COLORS.red, marginTop: 10 }}>
            {PROBLEM_REPORT.severity}
          </div>
          <div style={{ fontFamily: INTER, fontSize: 28, color: COLORS.offWhite, marginTop: 8 }}>
            {PROBLEM_REPORT.body}
          </div>
          {/* UNPROVEN stamp */}
          <div
            style={{
              position: "absolute",
              right: 36,
              top: 40,
              opacity: stamp * 0.92,
              transform: `rotate(-14deg) scale(${interpolate(stamp, [0, 1], [1.4, 1])})`,
              border: `4px solid ${COLORS.amber}`,
              color: COLORS.amber,
              fontFamily: MONO,
              fontSize: 34,
              fontWeight: 700,
              letterSpacing: 3,
              padding: "6px 16px",
              borderRadius: 8,
            }}
          >
            {PROBLEM_STAMP}
          </div>
        </div>

        <GlowText
          text={PROBLEM_HEADLINE}
          fontSize={52}
          color={COLORS.white}
          fontWeight={800}
          delay={60}
          style={{ marginTop: 56, textAlign: "center", maxWidth: 1300, letterSpacing: -0.5 }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
