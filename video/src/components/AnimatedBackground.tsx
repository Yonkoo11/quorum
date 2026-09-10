import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { ORBS } from "../constants";

export const AnimatedBackground: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      {ORBS.map((orb, i) => {
        const x = orb.baseX + Math.sin(frame * orb.speed + i * 1.5) * 90;
        const y = orb.baseY + Math.cos(frame * orb.speed + i * 2.1) * 70;
        return (
          <div key={i} style={{
            position: "absolute", left: x - orb.size / 2, top: y - orb.size / 2,
            width: orb.size, height: orb.size, borderRadius: "50%",
            background: orb.color, filter: `blur(${orb.blur}px)`, opacity: orb.opacity,
          }} />
        );
      })}
    </AbsoluteFill>
  );
};
