import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { AnimatedBackground } from "../components/AnimatedBackground";
import { GlowText } from "../components/GlowText";
import { COLORS } from "../constants";
import { INTER, MONO } from "../fonts";

const Side: React.FC<{
  delay: number;
  kicker: string;
  lines: string[];
  verdict: string;
  tone: "dim" | "live";
}> = ({ delay, kicker, lines, verdict, tone }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 18, stiffness: 80 } });
  const x = interpolate(s, [0, 1], [tone === "dim" ? -40 : 40, 0]);
  const live = tone === "live";
  const edge = live ? COLORS.accent : COLORS.muted;
  return (
    <div
      style={{
        opacity: s,
        transform: `translateX(${x}px)`,
        width: 640,
        background: live ? COLORS.bgCardStrong : "rgba(20,24,21,0.55)",
        border: `1px solid ${live ? COLORS.border : "rgba(90,110,94,0.28)"}`,
        borderRadius: 20,
        padding: "40px 42px",
      }}
    >
      <div
        style={{
          fontFamily: MONO,
          fontSize: 20,
          letterSpacing: 2,
          textTransform: "uppercase",
          color: edge,
          marginBottom: 26,
        }}
      >
        {kicker}
      </div>
      {lines.map((l, i) => (
        <div
          key={i}
          style={{
            fontFamily: INTER,
            fontSize: 34,
            fontWeight: 600,
            color: live ? COLORS.white : COLORS.offWhite,
            lineHeight: 1.45,
            marginBottom: 10,
          }}
        >
          {l}
        </div>
      ))}
      <div style={{ height: 1, background: live ? COLORS.border : "rgba(90,110,94,0.28)", margin: "28px 0 22px" }} />
      <div style={{ fontFamily: MONO, fontSize: 24, fontWeight: 700, color: live ? COLORS.accentBright : COLORS.muted }}>
        {verdict}
      </div>
    </div>
  );
};

export const Contrast: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      <AnimatedBackground />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <GlowText
          text="A flag is a claim. A drain is proof."
          fontSize={46}
          color={COLORS.white}
          fontWeight={700}
          style={{ marginBottom: 54 }}
        />
        <div style={{ display: "flex", gap: 40 }}>
          <Side
            delay={18}
            tone="dim"
            kicker="a scanner"
            lines={["flags a line.", "A report asserts", "impact."]}
            verdict="asserted"
          />
          <Side
            delay={30}
            tone="live"
            kicker="quorum"
            lines={["writes the exploit", "on a mainnet fork,", "keeps it only if the", "balance goes up."]}
            verdict="proven"
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
