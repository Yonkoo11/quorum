import React from "react";
import { AbsoluteFill, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { AnimatedBackground } from "../components/AnimatedBackground";
import { COLORS, FPS, TERMINAL_PARTS } from "../constants";
import { INTER, MONO } from "../fonts";

const Chrome: React.FC<{ chapter: string; live: boolean; children: React.ReactNode }> = ({
  chapter, live, children,
}) => (
  <div style={{
    width: 1740, borderRadius: 14, overflow: "hidden",
    border: `1px solid ${COLORS.border}`, boxShadow: `0 0 60px ${COLORS.accent}18`,
    background: COLORS.terminalBg,
  }}>
    <div style={{
      height: 46, display: "flex", alignItems: "center", gap: 9, padding: "0 18px",
      borderBottom: `1px solid ${COLORS.border}`, background: "rgba(0,0,0,0.35)",
    }}>
      <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#f85149" }} />
      <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#d29922" }} />
      <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#3fb950" }} />
      <span style={{ fontFamily: MONO, fontSize: 15, color: COLORS.muted, marginLeft: 12 }}>
        quorum — live session
      </span>
      <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 14 }}>
        {live && (
          <span style={{
            fontFamily: INTER, fontSize: 15, fontWeight: 700, color: COLORS.accentBright,
            border: `1px solid ${COLORS.borderStrong}`, borderRadius: 20, padding: "4px 14px",
          }}>UNCUT · REAL TIME</span>
        )}
        <span style={{ fontFamily: INTER, fontSize: 17, color: COLORS.offWhite }}>{chapter}</span>
      </div>
    </div>
    {children}
  </div>
);

export const TerminalScene: React.FC = () => {
  let offset = 0;
  const parts = TERMINAL_PARTS.map((p) => {
    const frames = Math.round((p.to - p.from) / p.rate);
    const seq = { ...p, from: offset, frames };
    offset += frames;
    return seq;
  });

  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      <AnimatedBackground />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        {parts.map((p, i) => (
          <Sequence key={i} from={p.from} durationInFrames={p.frames}>
            <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
              <Chrome chapter={p.chapter} live={p.rate === 1}>
                <OffthreadVideo
                  src={staticFile("video/terminal.mp4")}
                  startFrom={TERMINAL_PARTS[i].from}
                  endAt={TERMINAL_PARTS[i].to}
                  playbackRate={p.rate}
                  muted
                  style={{ width: 1740, height: 979, objectFit: "cover", display: "block" }}
                />
              </Chrome>
            </AbsoluteFill>
          </Sequence>
        ))}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
