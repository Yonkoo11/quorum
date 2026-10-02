import React from "react";
import { AbsoluteFill, Audio, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, PROOFS } from "./constants";
import { INTER, MONO } from "./fonts";

export const SOCIAL_W = 1080;
export const SOCIAL_H = 1920;
export const SOCIAL_FPS = 30;
export const SOCIAL_DURATION = 285; // 9.5s — covers the 8.45s hook narration + exit

/** The quorum mark: two overlapping lenses, only the overlap lit. */
const Mark: React.FC<{ size: number; opacity: number }> = ({ size, opacity }) => {
  const r = size / 2;
  const dx = r * 0.32;
  return (
    <svg width={size * 1.7} height={size} viewBox={`0 0 ${size * 1.7} ${size}`} style={{ opacity }}>
      <defs>
        <clipPath id="socialLensL">
          <circle cx={size * 0.85 - dx} cy={r} r={r * 0.92} />
        </clipPath>
      </defs>
      <circle cx={size * 0.85 - dx} cy={r} r={r * 0.92} fill="none" stroke={COLORS.accentDim} strokeWidth={3} />
      <circle cx={size * 0.85 + dx} cy={r} r={r * 0.92} fill="none" stroke={COLORS.accentDim} strokeWidth={3} />
      <g clipPath="url(#socialLensL)">
        <circle cx={size * 0.85 + dx} cy={r} r={r * 0.92} fill={COLORS.accent} />
      </g>
    </svg>
  );
};

const ProofChip: React.FC<{ name: string; amount: string; delay: number }> = ({ name, amount, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 18, stiffness: 90 } });
  return (
    <div
      style={{
        opacity: s,
        transform: `translateY(${interpolate(s, [0, 1], [20, 0])}px)`,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        width: 820,
        background: COLORS.bgCardStrong,
        border: `1px solid ${COLORS.border}`,
        borderRadius: 18,
        padding: "26px 36px",
      }}
    >
      <div style={{ fontFamily: INTER, fontSize: 40, fontWeight: 600, color: COLORS.white }}>{name}</div>
      <div style={{ fontFamily: MONO, fontSize: 44, fontWeight: 700, color: COLORS.accentBright }}>{amount}</div>
    </div>
  );
};

export const SocialClip: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const markIn = spring({ frame, fps, config: { damping: 200 } });
  const titleIn = spring({ frame: frame - 16, fps, config: { damping: 200 } });
  const closeIn = spring({ frame: frame - 230, fps, config: { damping: 200 } });
  const exit = interpolate(frame, [SOCIAL_DURATION - 18, SOCIAL_DURATION], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg, opacity: exit }}>
      <Audio src={staticFile("audio/hook.mp3")} volume={1} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: 0.06, transform: "scale(2.6)" }}>
        <Mark size={520} opacity={1} />
      </AbsoluteFill>

      <AbsoluteFill style={{ alignItems: "center", padding: "150px 0 0" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 22, opacity: markIn }}>
          <Mark size={62} opacity={1} />
          <div style={{ fontFamily: MONO, fontSize: 46, fontWeight: 700, color: COLORS.accent, letterSpacing: 1 }}>
            quorum
          </div>
        </div>

        <div
          style={{
            opacity: titleIn,
            transform: `translateY(${interpolate(titleIn, [0, 1], [26, 0])}px)`,
            fontFamily: INTER,
            fontSize: 96,
            fontWeight: 900,
            color: COLORS.white,
            textAlign: "center",
            lineHeight: 1.05,
            letterSpacing: -2,
            marginTop: 70,
          }}
        >
          Prove it.
          <br />
          <span style={{ color: COLORS.accent }}>Or drop it.</span>
        </div>

        <Sequence from={70} layout="none">
          <div style={{ display: "flex", flexDirection: "column", gap: 28, marginTop: 96 }}>
            {PROOFS.map((p, i) => (
              <ProofChip key={p.name} name={p.name} amount={p.amount} delay={i * 10} />
            ))}
          </div>
        </Sequence>

        <div
          style={{
            opacity: closeIn,
            transform: `translateY(${interpolate(closeIn, [0, 1], [20, 0])}px)`,
            marginTop: 90,
            textAlign: "center",
          }}
        >
          <div style={{ fontFamily: INTER, fontSize: 42, fontWeight: 600, color: COLORS.offWhite, lineHeight: 1.4 }}>
            Four real 2026 hacks,
            <br />
            reproduced on a fork to the wei.
          </div>
          <div style={{ fontFamily: MONO, fontSize: 40, fontWeight: 700, color: COLORS.accentBright, marginTop: 34 }}>
            runquorum.site
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
