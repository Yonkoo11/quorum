import React from "react";
import { AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { AnimatedBackground } from "../components/AnimatedBackground";
import { GlowText } from "../components/GlowText";
import { CHAINS, CLAIM_FEE, COLORS, RH_TX } from "../constants";
import { INTER, MONO } from "../fonts";

const Step: React.FC<{ delay: number; label: string; value: string; icon: string }> = ({
  delay,
  label,
  value,
  icon,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 18, stiffness: 90 } });
  return (
    <div
      style={{
        opacity: s,
        transform: `translateX(${interpolate(s, [0, 1], [-20, 0])}px)`,
        display: "flex",
        alignItems: "center",
        gap: 20,
        padding: "14px 0",
      }}
    >
      <div
        style={{
          width: 44,
          height: 44,
          borderRadius: 10,
          background: COLORS.accentGlow,
          border: `1px solid ${COLORS.border}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 24,
        }}
      >
        {icon}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontFamily: INTER, fontSize: 26, fontWeight: 600, color: COLORS.white }}>{label}</div>
        <div style={{ fontFamily: MONO, fontSize: 20, color: COLORS.accentBright, marginTop: 2 }}>{value}</div>
      </div>
    </div>
  );
};

const ChainBadge: React.FC<{ delay: number; name: string; id: string; addr: string }> = ({
  delay,
  name,
  id,
  addr,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 16, stiffness: 90 } });
  return (
    <div
      style={{
        opacity: s,
        transform: `translateY(${interpolate(s, [0, 1], [18, 0])}px)`,
        background: COLORS.bgCardStrong,
        border: `1px solid ${COLORS.borderStrong}`,
        borderRadius: 14,
        padding: "18px 28px",
        minWidth: 330,
        boxShadow: `0 0 30px ${COLORS.accent}22`,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ width: 9, height: 9, borderRadius: "50%", background: COLORS.accentBright }} />
        <div style={{ fontFamily: INTER, fontSize: 26, fontWeight: 700, color: COLORS.white }}>{name}</div>
      </div>
      <div style={{ fontFamily: MONO, fontSize: 17, color: COLORS.muted, marginTop: 8 }}>{id}</div>
      <div style={{ fontFamily: MONO, fontSize: 19, color: COLORS.offWhite, marginTop: 4 }}>{addr}</div>
    </div>
  );
};

export const OnChain: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      <AnimatedBackground />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <GlowText text="A proof is not a PDF." fontSize={48} color={COLORS.white} fontWeight={800} style={{ marginBottom: 14 }} />
        <GlowText
          text="Each one settles as a paid on-chain claim."
          fontSize={30}
          color={COLORS.offWhite}
          fontWeight={500}
          delay={12}
          style={{ marginBottom: 40 }}
        />

        <Sequence from={120} layout="none">
          <div
            style={{
              background: COLORS.bgCard,
              border: `1px solid ${COLORS.border}`,
              borderRadius: 18,
              padding: "26px 44px",
              width: 760,
            }}
          >
            <div style={{ fontFamily: MONO, fontSize: 18, color: COLORS.muted, marginBottom: 6 }}>
              ClaimRegistry.claim(digest) — one transaction
            </div>
            <Step delay={10} icon="🔥" label="Fee burned" value={`${CLAIM_FEE} — pulled and burned`} />
            <Step delay={26} icon="🔗" label="Digest recorded" value={RH_TX} />
            <Step delay={42} icon="✓" label="No record without its own cost" value="invariant: burn before claim" />
          </div>
        </Sequence>

        <Sequence from={350} layout="none">
          <div style={{ display: "flex", gap: 30, marginTop: 42 }}>
            {CHAINS.map((c, i) => (
              <ChainBadge key={c.name} delay={i * 8} name={c.name} id={c.id} addr={c.addr} />
            ))}
          </div>
        </Sequence>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
