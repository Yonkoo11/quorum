import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { AnimatedBackground } from "../components/AnimatedBackground";
import { COLORS, TERMINAL, TERMINAL_CMD, TERMINAL_LINES } from "../constants";
import { INTER, MONO } from "../fonts";

const LINE_START = 56; // frame the first output line appears
const LINE_STEP = 20; // frames between output lines

const OutLine: React.FC<{ index: number; text: string; color: string; bold?: boolean }> = ({
  index,
  text,
  color,
  bold,
}) => {
  const frame = useCurrentFrame();
  const start = LINE_START + index * LINE_STEP;
  const appear = interpolate(frame, [start, start + 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const glow = bold ? interpolate(frame, [start, start + 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;
  return (
    <div
      style={{
        opacity: appear,
        fontFamily: MONO,
        fontSize: 29,
        lineHeight: 1.5,
        color,
        fontWeight: bold ? 700 : 400,
        textShadow: bold ? `0 0 ${18 * glow}px ${COLORS.accent}aa` : "none",
        whiteSpace: "pre",
      }}
    >
      {text}
    </div>
  );
};

export const TerminalScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const cardIn = spring({ frame, fps, config: { damping: 200, mass: 0.7 } });
  const typed = Math.max(0, Math.min(TERMINAL_CMD.length, Math.round((frame - 6) * 1.7)));

  const calloutStart = LINE_START + TERMINAL_LINES.length * LINE_STEP + 16;
  const cS = spring({ frame: frame - calloutStart, fps, config: { damping: 18, stiffness: 90 } });

  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      <AnimatedBackground />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <div
          style={{
            opacity: cardIn,
            transform: `scale(${interpolate(cardIn, [0, 1], [0.97, 1])})`,
            width: 1340,
            background: TERMINAL.bg,
            border: `1px solid ${COLORS.border}`,
            borderRadius: 16,
            padding: "30px 40px 38px",
            boxShadow: "0 30px 80px rgba(0,0,0,0.5)",
          }}
        >
          {/* window chrome */}
          <div style={{ display: "flex", gap: 9, marginBottom: 24 }}>
            {["#f85149", "#d29922", "#3fb950"].map((c) => (
              <div key={c} style={{ width: 14, height: 14, borderRadius: "50%", background: c, opacity: 0.8 }} />
            ))}
            <div style={{ fontFamily: MONO, fontSize: 18, color: COLORS.muted, marginLeft: 14 }}>
              prove — ethereum · block 25170513
            </div>
          </div>
          {/* command */}
          <div style={{ fontFamily: MONO, fontSize: 29, color: TERMINAL.text, marginBottom: 18, whiteSpace: "pre-wrap" }}>
            <span style={{ color: TERMINAL.prompt }}>$ </span>
            {TERMINAL_CMD.slice(0, typed)}
            {typed < TERMINAL_CMD.length && frame > 2 ? <span style={{ color: COLORS.accent }}>▋</span> : null}
          </div>
          {/* output */}
          {TERMINAL_LINES.map((l, i) => (
            <OutLine key={i} index={i} text={l.text} color={TERMINAL[l.color]} bold={l.bold} />
          ))}
        </div>

        {/* drain callout */}
        <div
          style={{
            opacity: cS,
            transform: `translateY(${interpolate(cS, [0, 1], [24, 0])}px)`,
            marginTop: 34,
            display: "flex",
            alignItems: "center",
            gap: 16,
          }}
        >
          <div style={{ fontFamily: MONO, fontSize: 52, fontWeight: 700, color: COLORS.accentBright }}>+712.63 USDC</div>
          <div style={{ fontFamily: INTER, fontSize: 28, color: COLORS.offWhite }}>drained from a real victim Safe, on a fork</div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
