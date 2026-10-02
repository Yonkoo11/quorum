import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { AnimatedBackground } from "../components/AnimatedBackground";
import { GlowText } from "../components/GlowText";
import { CLOSE_EVENT, CLOSE_URL, COLORS } from "../constants";
import { INTER, MONO } from "../fonts";

export const Close: React.FC = () => {
  const frame = useCurrentFrame();
  const line = interpolate(frame, [28, 54], [0, 440], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      <AnimatedBackground />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <GlowText text="quorum" fontSize={122} color={COLORS.accent} fontFamily={MONO} fontWeight={700} />
        <GlowText
          text="Prove it. Or drop it."
          fontSize={48}
          color={COLORS.white}
          fontWeight={700}
          delay={12}
          style={{ marginTop: 18 }}
        />
        <div style={{ height: 2, width: line, background: COLORS.borderStrong, margin: "38px 0 32px" }} />
        <GlowText text={CLOSE_URL} fontSize={34} color={COLORS.accentBright} fontWeight={600} delay={34} fontFamily={MONO} />
        <div style={{ fontFamily: INTER, fontSize: 24, color: COLORS.offWhite, marginTop: 18 }}>
          Live on Robinhood Chain and Arbitrum One
        </div>
        <div style={{ fontFamily: MONO, fontSize: 19, color: COLORS.muted, marginTop: 10 }}>{CLOSE_EVENT}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
