import React from "react";
import { AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { AnimatedBackground } from "../components/AnimatedBackground";
import { GlowText } from "../components/GlowText";
import { COLORS, COMPARE_ROWS, RECALL_HEADLINE, RECALL_SERIES, RECALL_SUB } from "../constants";
import { INTER, MONO } from "../fonts";

const CW = 760;
const CH = 260;
const PAD = 16;

const RecallChart: React.FC = () => {
  const frame = useCurrentFrame();
  const n = RECALL_SERIES.length;
  const max = 100;
  const pts = RECALL_SERIES.map((v, i) => {
    const x = PAD + (i / (n - 1)) * (CW - PAD * 2);
    const y = CH - PAD - (v / max) * (CH - PAD * 2);
    return { x, y, v };
  });
  // reveal: how many points are "drawn" so far
  const prog = interpolate(frame, [10, 95], [0, n - 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const shown = pts.filter((_, i) => i <= prog);
  const path = shown.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  const last = shown[shown.length - 1];
  return (
    <svg width={CW} height={CH} style={{ overflow: "visible" }}>
      {/* baseline */}
      <line x1={PAD} y1={CH - PAD} x2={CW - PAD} y2={CH - PAD} stroke={COLORS.border} strokeWidth={1} />
      {/* area */}
      {shown.length > 1 && (
        <path
          d={`${path} L${last.x.toFixed(1)},${(CH - PAD).toFixed(1)} L${PAD},${(CH - PAD).toFixed(1)} Z`}
          fill={COLORS.accent}
          opacity={0.1}
        />
      )}
      {shown.length > 1 && <path d={path} fill="none" stroke={COLORS.accent} strokeWidth={3} />}
      {shown.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={i === shown.length - 1 ? 6 : 3.5} fill={COLORS.accentBright} />
      ))}
      {last && (
        <text x={last.x} y={last.y - 16} fill={COLORS.white} fontFamily={MONO} fontSize={26} fontWeight={700} textAnchor="end">
          {last.v}%
        </text>
      )}
    </svg>
  );
};

const CompareRow: React.FC<{
  risk: string;
  quorum: string;
  slither: string;
  win: "quorum" | "slither";
  delay: number;
}> = ({ risk, quorum, slither, win, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 18, stiffness: 90 } });
  const cell = (label: string, value: string, winner: boolean) => (
    <div style={{ textAlign: "center", minWidth: 150 }}>
      <div style={{ fontFamily: MONO, fontSize: 16, color: COLORS.muted, marginBottom: 4 }}>{label}</div>
      <div style={{ fontFamily: MONO, fontSize: 30, fontWeight: 700, color: winner ? COLORS.accentBright : COLORS.offWhite }}>
        {value}
      </div>
    </div>
  );
  return (
    <div
      style={{
        opacity: s,
        transform: `translateY(${interpolate(s, [0, 1], [16, 0])}px)`,
        display: "flex",
        alignItems: "center",
        gap: 40,
        background: COLORS.bgCard,
        border: `1px solid ${COLORS.border}`,
        borderRadius: 14,
        padding: "16px 34px",
      }}
    >
      <div style={{ fontFamily: INTER, fontSize: 26, fontWeight: 600, color: COLORS.white, minWidth: 220 }}>{risk}</div>
      {cell("Quorum", quorum, win === "quorum")}
      {cell("Slither", slither, win === "slither")}
      <div
        style={{
          fontFamily: MONO,
          fontSize: 18,
          color: win === "quorum" ? COLORS.accent : COLORS.amber,
          minWidth: 130,
          textAlign: "right",
        }}
      >
        {win === "quorum" ? "Quorum wins" : "Slither wins"}
      </div>
    </div>
  );
};

export const Numbers: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      <AnimatedBackground />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <GlowText
          text="It publishes its own miss rate."
          fontSize={46}
          color={COLORS.white}
          fontWeight={700}
          style={{ marginBottom: 30 }}
        />
        <div style={{ display: "flex", alignItems: "center", gap: 60 }}>
          <RecallChart />
          <div style={{ textAlign: "left" }}>
            <GlowText text={RECALL_HEADLINE} fontSize={120} color={COLORS.accent} fontWeight={900} fontFamily={MONO} delay={70} />
            <div style={{ fontFamily: INTER, fontSize: 24, color: COLORS.offWhite, marginTop: 4, maxWidth: 320 }}>
              {RECALL_SUB}
            </div>
          </div>
        </div>
        <Sequence from={225} layout="none">
          <div style={{ display: "flex", flexDirection: "column", gap: 14, marginTop: 44 }}>
            {COMPARE_ROWS.map((r, i) => (
              <CompareRow key={r.risk} {...r} delay={i * 8} />
            ))}
          </div>
        </Sequence>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
