import React from "react";
import { AbsoluteFill, Audio, Sequence, interpolate, staticFile } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { AUDIO_DURATIONS, AUDIO_FILES, COLORS, CROSSFADE, SCENE_DURATIONS, SCENE_ORDER, SceneKey } from "./constants";
import { Subtitles } from "./Subtitles";
import { Hook } from "./scenes/Hook";
import { Contrast } from "./scenes/Contrast";
import { TerminalScene } from "./scenes/TerminalScene";
import { Numbers } from "./scenes/Numbers";
import { OnChain } from "./scenes/OnChain";
import { Close } from "./scenes/Close";

const SCENES: Record<SceneKey, React.FC> = {
  hook: Hook,
  contrast: Contrast,
  terminal: TerminalScene,
  numbers: Numbers,
  onchain: OnChain,
  close: Close,
};

/** One scene's narration clip, placed at its own start, with a short fade at each end. */
const Line: React.FC<{ file: string; frames: number }> = ({ file, frames }) => (
  <Audio
    src={staticFile(file)}
    volume={(f) =>
      Math.min(
        interpolate(f, [0, 4], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
        interpolate(f, [frames - 8, frames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
      )
    }
  />
);

export const MainVideo: React.FC = () => {
  const timing = linearTiming({ durationInFrames: CROSSFADE });

  // Audio: one clip per scene, placed at the scene's global start frame.
  let offset = 0;
  const narration = SCENE_ORDER.map((key, i) => {
    const base = offset;
    offset += SCENE_DURATIONS[key] - (i < SCENE_ORDER.length - 1 ? CROSSFADE : 0);
    const frames = AUDIO_DURATIONS[key];
    return (
      <Sequence key={`a-${key}`} from={base} durationInFrames={frames}>
        <Line file={AUDIO_FILES[key]} frames={frames} />
      </Sequence>
    );
  });

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg }}>
      <TransitionSeries>
        {SCENE_ORDER.flatMap((key, i) => {
          const Scene = SCENES[key];
          const nodes = [
            <TransitionSeries.Sequence key={key} durationInFrames={SCENE_DURATIONS[key]}>
              <Scene />
            </TransitionSeries.Sequence>,
          ];
          if (i < SCENE_ORDER.length - 1) {
            nodes.push(<TransitionSeries.Transition key={`t-${key}`} presentation={fade()} timing={timing} />);
          }
          return nodes;
        })}
      </TransitionSeries>
      {narration}
      <Subtitles />
    </AbsoluteFill>
  );
};
