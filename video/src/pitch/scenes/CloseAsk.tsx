import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { AnimatedBackground } from "../../components/AnimatedBackground";
import { GlowText } from "../../components/GlowText";
import { CLOSE, COLORS } from "../constants";
import { INTER, MONO } from "../../fonts";

export const CloseAsk: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const chip = spring({ frame: frame - 207, fps, config: { damping: 16, stiffness: 90 } });
  const line = interpolate(frame, [505, 540], [0, 440], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      <AnimatedBackground />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: "0 180px" }}>
        <GlowText text="quorum" fontSize={64} color={COLORS.accent} fontFamily={MONO} fontWeight={700} />
        <GlowText
          text={CLOSE.market}
          fontSize={30}
          color={COLORS.offWhite}
          fontWeight={500}
          delay={14}
          style={{ marginTop: 22, textAlign: "center", maxWidth: 1200, lineHeight: 1.4 }}
        />

        {/* chains badge */}
        <div
          style={{
            opacity: chip,
            transform: `translateY(${interpolate(chip, [0, 1], [16, 0])}px)`,
            marginTop: 30,
            display: "flex",
            alignItems: "center",
            gap: 12,
            background: COLORS.bgCardStrong,
            border: `1px solid ${COLORS.borderStrong}`,
            borderRadius: 999,
            padding: "12px 26px",
          }}
        >
          <div style={{ width: 9, height: 9, borderRadius: "50%", background: COLORS.accentBright }} />
          <div style={{ fontFamily: INTER, fontSize: 24, fontWeight: 600, color: COLORS.white }}>{CLOSE.chains}</div>
        </div>

        <GlowText
          text={CLOSE.roadmap}
          fontSize={25}
          color={COLORS.offWhite}
          fontWeight={500}
          delay={270}
          style={{ marginTop: 28, textAlign: "center", maxWidth: 1180, lineHeight: 1.45 }}
        />

        <div style={{ height: 2, width: line, background: COLORS.borderStrong, margin: "40px 0 28px" }} />

        <GlowText text={CLOSE.tagline} fontSize={56} color={COLORS.white} fontWeight={900} delay={508} style={{ letterSpacing: -1 }} />
        <GlowText text={CLOSE.url} fontSize={34} color={COLORS.accentBright} fontFamily={MONO} fontWeight={700} delay={530} style={{ marginTop: 16 }} />
        <GlowText text={CLOSE.event} fontSize={19} color={COLORS.muted} fontFamily={MONO} delay={545} style={{ marginTop: 14 }} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
