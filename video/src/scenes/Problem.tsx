import React from "react";
import { AbsoluteFill, Sequence, interpolate, useCurrentFrame, useVideoConfig, spring } from "remotion";
import { AnimatedBackground } from "../components/AnimatedBackground";
import { GlowText } from "../components/GlowText";
import { Lens } from "../components/Lens";
import { COLORS } from "../constants";
import { INTER, MONO } from "../fonts";

const NAMES = ["callorder", "guard", "modifier", "sender", "unchecked", "precision"];

const Verdict: React.FC<{ text: string; x: number; y: number; delay: number }> = ({ text, x, y, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const prog = spring({ frame: frame - delay, fps, config: { damping: 18, stiffness: 110 } });
  const op = interpolate(prog, [0, 0.4], [0, 1], { extrapolateRight: "clamp" });
  const drift = interpolate(prog, [0, 1], [10, 0]);
  return (
    <div style={{
      position: "absolute", left: x, top: y + drift, opacity: op,
      fontFamily: MONO, fontSize: 19, color: COLORS.amber,
    }}>{text}</div>
  );
};

export const Problem: React.FC = () => {
  const frame = useCurrentFrame();
  const strike = interpolate(frame, [300, 340], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      <AnimatedBackground />
      <AbsoluteFill style={{ alignItems: "center", paddingTop: 86 }}>
        <GlowText text="six agents, six opinions" fontSize={62} color={COLORS.white} fontWeight={700} />
        <div style={{ fontFamily: INTER, fontSize: 30, color: COLORS.offWhite, marginTop: 16 }}>
          nothing between them but your patience
        </div>
      </AbsoluteFill>

      {NAMES.map((n, i) => (
        <Lens key={n} label={n} delay={10 + i * 7} state="alone"
              x={128 + (i % 3) * 560} y={i < 3 ? 300 : 560} />
      ))}

      <Sequence from={120}>
        <AbsoluteFill>
          <Verdict text="scanned Vault.sol" x={128} y={392} delay={0} />
          <Verdict text="scanned Vault.sol" x={688} y={392} delay={14} />
          <Verdict text="scanned Vault.sol" x={1248} y={392} delay={26} />
          <Verdict text="re-reported a finding you retired" x={128} y={652} delay={40} />
          <Verdict text="re-found last week's bug" x={688} y={652} delay={54} />
          <Verdict text="scanned Vault.sol" x={1248} y={652} delay={66} />
        </AbsoluteFill>
      </Sequence>

      <Sequence from={296}>
        <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 168 }}>
          <div style={{ position: "relative" }}>
            <div style={{ fontFamily: INTER, fontSize: 42, fontWeight: 700, color: COLORS.red }}>
              same file, six times, zero agreement
            </div>
            <div style={{
              position: "absolute", left: 0, top: "52%", height: 3, background: COLORS.red,
              width: `${strike * 100}%`, opacity: 0.85,
            }} />
          </div>
        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};
