import React from "react";
import { AbsoluteFill, Audio, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "./constants";
import { INTER, MONO } from "./fonts";

export const SOCIAL_W = 1080;
export const SOCIAL_H = 1920;
export const SOCIAL_FPS = 30;
export const SOCIAL_DURATION = 11 * SOCIAL_FPS; // 330 frames

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

/** One real command and its real result. */
const RunPanel: React.FC<{
  start: number;
  cmd: string;
  confirmed: number;
  tone: string;
  note: string;
}> = ({ start, cmd, confirmed, tone, note }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const local = frame - start;
  const s = spring({ frame: local, fps, config: { damping: 200, mass: 0.6 } });
  const y = interpolate(s, [0, 1], [34, 0]);
  const scale = interpolate(s, [0, 1], [0.96, 1]);

  // characters typed so far, so the command writes itself on
  const typed = Math.max(0, Math.min(cmd.length, Math.round(local * 1.6)));

  return (
    <div
      style={{
        opacity: s,
        transform: `translateY(${y}px) scale(${scale})`,
        background: COLORS.bgCard,
        border: `1px solid ${tone === COLORS.red ? "rgba(248,81,73,0.34)" : COLORS.border}`,
        borderRadius: 22,
        padding: "44px 46px",
        width: 880,
      }}
    >
      <div style={{ fontFamily: MONO, fontSize: 34, color: COLORS.offWhite, height: 46 }}>
        <span style={{ color: COLORS.muted }}>$ </span>
        {cmd.slice(0, typed)}
        {typed < cmd.length && local > 0 ? <span style={{ color: COLORS.accent }}>▋</span> : null}
      </div>
      <div style={{ height: 1, background: COLORS.border, margin: "30px 0 34px" }} />
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
        <div>
          <div style={{ fontFamily: MONO, fontSize: 82, fontWeight: 700, color: COLORS.white, lineHeight: 1 }}>12</div>
          <div style={{ fontFamily: MONO, fontSize: 27, color: COLORS.muted, marginTop: 12 }}>lens-units scanned</div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontFamily: MONO, fontSize: 82, fontWeight: 700, color: tone, lineHeight: 1 }}>{confirmed}</div>
          <div style={{ fontFamily: MONO, fontSize: 27, color: COLORS.muted, marginTop: 12 }}>confirmed</div>
        </div>
      </div>
      <div style={{ height: 1, background: COLORS.border, margin: "34px 0 26px" }} />
      <div style={{ fontFamily: MONO, fontSize: 25, color: COLORS.muted }}>{note}</div>
    </div>
  );
};

export const SocialClip: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const markIn = spring({ frame, fps, config: { damping: 200 } });
  const titleIn = spring({ frame: frame - 18, fps, config: { damping: 200 } });
  const closeIn = spring({ frame: frame - 250, fps, config: { damping: 200 } });
  const exit = interpolate(frame, [SOCIAL_DURATION - 20, SOCIAL_DURATION], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg, opacity: exit }}>
      <Audio src={staticFile("audio/social-sd.wav")} volume={1} />
      {/* the mechanic, faint, behind everything */}
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          opacity: 0.06,
          transform: "scale(2.6)",
        }}
      >
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
            fontSize: 74,
            fontWeight: 800,
            color: COLORS.white,
            textAlign: "center",
            lineHeight: 1.12,
            letterSpacing: -1.5,
            marginTop: 74,
          }}
        >
          Same files.
          <br />
          Same checkers.
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 40, marginTop: 92 }}>
          <RunPanel
            start={70}
            cmd="quorum run"
            confirmed={2}
            tone={COLORS.accentBright}
            note="both lenses agreed, so it published"
          />
          <RunPanel
            start={150}
            cmd="quorum run --no-memory"
            confirmed={0}
            tone={COLORS.red}
            note="both lenses saw it, neither knew"
          />
        </div>

        <div
          style={{
            opacity: closeIn,
            transform: `translateY(${interpolate(closeIn, [0, 1], [20, 0])}px)`,
            marginTop: 104,
            textAlign: "center",
          }}
        >
          <div style={{ fontFamily: INTER, fontSize: 40, fontWeight: 600, color: COLORS.offWhite, lineHeight: 1.4 }}>
            They lost the only place
            <br />
            they could meet.
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
