import React from "react";
import { AbsoluteFill, Audio, Sequence, interpolate, staticFile } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { COLORS, CROSSFADE, FPS, SCENE_DURATIONS, SCENE_ORDER, TIMING } from "./constants";
import { Subtitles } from "./Subtitles";
import { Hook } from "./scenes/Hook";
import { Problem } from "./scenes/Problem";
import { Mechanic } from "./scenes/Mechanic";
import { TerminalScene } from "./scenes/TerminalScene";
import { Close } from "./scenes/Close";

const SCENES = { hook: Hook, problem: Problem, mechanic: Mechanic, terminal: TerminalScene, close: Close };

/** One clip per spoken sentence, placed at its own start, with a short fade at each end. */
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
  let offset = 0;

  const narration = SCENE_ORDER.flatMap((key, i) => {
    const base = offset;
    offset += SCENE_DURATIONS[key] - (i < SCENE_ORDER.length - 1 ? CROSSFADE : 0);
    return TIMING[key].items.map((item, j) => {
      const frames = Math.round(item.dur * FPS);
      return (
        <Sequence key={`${key}-${j}`} from={base + Math.round(item.start * FPS)} durationInFrames={frames}>
          <Line file={item.file} frames={frames} />
        </Sequence>
      );
    });
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
            nodes.push(
              <TransitionSeries.Transition key={`t-${key}`} presentation={fade()} timing={timing} />,
            );
          }
          return nodes;
        })}
      </TransitionSeries>
      {narration}
      <Subtitles />
    </AbsoluteFill>
  );
};
