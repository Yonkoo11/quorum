import React from "react";
import { AbsoluteFill, Img, OffthreadVideo, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { UI_COLORS as C, UI_CROSSFADE, UI_SCENES, UiScene } from "./constants";
import { DISPLAY, SANS } from "./fonts";

/** Spring entrance used everywhere: opacity from 0, scale from 0.93, a small rise. */
const useEnter = (delay = 0) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - delay, fps, config: { damping: 16, stiffness: 140 } });
  return {
    opacity: interpolate(p, [0, 0.4], [0, 1], { extrapolateRight: "clamp" }),
    transform: `translateY(${interpolate(p, [0, 1], [16, 0])}px) scale(${interpolate(p, [0, 1], [0.93, 1])})`,
  };
};

/** The lens mark from the site: two circles, the intersection filled. */
const Mark: React.FC<{ size?: number; color?: string; fill?: string }> = ({ size = 44, color = C.ink, fill = C.green }) => (
  <svg width={size * 56 / 38} height={size} viewBox="0 0 56 38" aria-hidden="true">
    <defs>
      <clipPath id="ui-lens-clip"><circle cx="19" cy="19" r="17" /></clipPath>
    </defs>
    <g clipPath="url(#ui-lens-clip)"><circle cx="37" cy="19" r="17" fill={fill} /></g>
    <circle cx="19" cy="19" r="17" fill="none" stroke={color} strokeWidth="3" />
    <circle cx="37" cy="19" r="17" fill="none" stroke={color} strokeWidth="3" />
  </svg>
);

/** Height of the caption band under every recording; the recording above it is cropped at the bottom, never covered. */
const BAND = 84;

/** The caption band: paper, ruled at the top, the beat's label left in tracked caps, the site's address right. */
const Band: React.FC<{ text: string; delay?: number }> = ({ text, delay = 4 }) => {
  const enter = useEnter(delay);
  return (
    <div
      style={{
        position: "absolute", left: 0, right: 0, bottom: 0, height: BAND, background: C.paper, color: C.ink,
        borderTop: `3px solid ${C.ink}`, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 56px",
        fontFamily: SANS, fontWeight: 500, fontSize: 24, letterSpacing: "0.2em", textTransform: "uppercase", lineHeight: 1,
      }}
    >
      <span style={enter}>{text}</span>
      <span style={{ color: C.muted }}>runquorum.site</span>
    </div>
  );
};

const TitleScene: React.FC<{ scene: Extract<UiScene, { kind: "title" }> }> = ({ scene }) => {
  const label = useEnter(0);
  const l1 = useEnter(6);
  const l2 = useEnter(12);
  const mark = useEnter(18);
  return (
    <AbsoluteFill style={{ background: C.paper, color: C.ink, padding: "0 120px", justifyContent: "center" }}>
      <div style={{ fontFamily: SANS, fontWeight: 500, fontSize: 26, letterSpacing: "0.24em", textTransform: "uppercase", color: C.muted, marginBottom: 36, ...label }}>
        {scene.label}
      </div>
      <div style={{ fontFamily: DISPLAY, fontSize: 168, lineHeight: 0.92, letterSpacing: "-0.03em", textTransform: "uppercase" }}>
        <div style={l1}>{scene.lines[0]}</div>
        <div style={{ color: C.greenText, ...l2 }}>{scene.lines[1]}</div>
      </div>
      <div style={{ position: "absolute", right: 120, top: 120, ...mark }}>
        <Mark size={220} />
      </div>
    </AbsoluteFill>
  );
};

const ClipScene: React.FC<{ scene: Extract<UiScene, { kind: "clip" }> }> = ({ scene }) => (
  <AbsoluteFill style={{ background: C.paper }}>
    <div style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080 - BAND, overflow: "hidden" }}>
      <OffthreadVideo src={staticFile(scene.file)} muted style={{ width: 1920, height: 1080, objectFit: "cover" }} />
    </div>
    <Band text={scene.label} />
  </AbsoluteFill>
);

const PhoneScene: React.FC<{ scene: Extract<UiScene, { kind: "phone" }> }> = ({ scene }) => {
  const enter = useEnter(0);
  const h = 880; const w = Math.round(h * 390 / 844);
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080 - BAND, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ width: w, height: h, border: `3px solid ${C.ink}`, boxShadow: `10px 10px 0 ${C.ink}`, background: C.surface, overflow: "hidden", ...enter }}>
          <OffthreadVideo src={staticFile(scene.file)} muted style={{ width: w, height: h, objectFit: "cover" }} />
        </div>
      </div>
      <Band text={scene.label} />
    </AbsoluteFill>
  );
};

const CloseScene: React.FC<{ scene: Extract<UiScene, { kind: "close" }> }> = ({ scene }) => {
  const band = useEnter(8);
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <Img src={staticFile(scene.still)} style={{ width: 1920, height: 1080, objectFit: "cover" }} />
      <div style={{ position: "absolute", left: 0, bottom: 0, right: 0, padding: "56px 120px 72px", ...band }}>
        <div style={{ display: "inline-block", background: C.paper, color: C.ink, border: `3px solid ${C.ink}`, boxShadow: `10px 10px 0 ${C.green}`, padding: "40px 56px" }}>
          <div style={{ fontFamily: DISPLAY, fontSize: 120, lineHeight: 0.95, letterSpacing: "-0.03em", textTransform: "uppercase" }}>{scene.lines[0]}</div>
          <div style={{ fontFamily: SANS, fontWeight: 500, fontSize: 26, letterSpacing: "0.2em", textTransform: "uppercase", color: C.muted, marginTop: 22 }}>{scene.label}</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Scene: React.FC<{ scene: UiScene }> = ({ scene }) => {
  switch (scene.kind) {
    case "title": return <TitleScene scene={scene} />;
    case "clip": return <ClipScene scene={scene} />;
    case "phone": return <PhoneScene scene={scene} />;
    case "close": return <CloseScene scene={scene} />;
  }
};

export const UiLaunch: React.FC = () => {
  const timing = linearTiming({ durationInFrames: UI_CROSSFADE });
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <TransitionSeries>
        {UI_SCENES.flatMap((scene, i) => {
          const items = [
            <TransitionSeries.Sequence key={scene.key} durationInFrames={scene.frames}>
              <Scene scene={scene} />
            </TransitionSeries.Sequence>,
          ];
          if (i < UI_SCENES.length - 1) {
            items.push(<TransitionSeries.Transition key={`t-${scene.key}`} presentation={fade()} timing={timing} />);
          }
          return items;
        })}
      </TransitionSeries>
    </AbsoluteFill>
  );
};
