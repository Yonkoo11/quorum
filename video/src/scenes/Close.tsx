import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { AnimatedBackground } from "../components/AnimatedBackground";
import { GlowText } from "../components/GlowText";
import { COLORS } from "../constants";
import { INTER, MONO } from "../fonts";

export const Close: React.FC = () => {
  const frame = useCurrentFrame();
  const line = interpolate(frame, [30, 58], [0, 420], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      <AnimatedBackground />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <GlowText text="quorum" fontSize={118} color={COLORS.accent} fontFamily={MONO} fontWeight={700} />
        <GlowText text="memory is the coordination layer" fontSize={44} color={COLORS.white}
                  fontWeight={600} delay={14} style={{ marginTop: 22 }} />
        <div style={{ height: 2, width: line, background: COLORS.borderStrong, margin: "40px 0 34px" }} />
        <GlowText text="github.com/Yonkoo11/quorum" fontSize={30} color={COLORS.offWhite}
                  fontWeight={500} delay={40} fontFamily={MONO} />
        <div style={{ fontFamily: INTER, fontSize: 22, color: COLORS.muted, marginTop: 20 }}>
          Sibyl Memory · Base mainnet · claim 0xa648821d
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
