import React from "react";
import { AbsoluteFill, Audio, Sequence, interpolate, staticFile } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { AUDIO_DURATIONS, AUDIO_FILES, COLORS, CROSSFADE, SCENE_DURATIONS, SCENE_ORDER, PScene } from "./constants";
import { PitchSubtitles } from "./Subtitles";
import { Problem } from "./scenes/Problem";
import { Solution } from "./scenes/Solution";
import { Traction } from "./scenes/Traction";
import { Moat } from "./scenes/Moat";
import { CloseAsk } from "./scenes/CloseAsk";

const SCENES: Record<PScene, React.FC> = {
  problem: Problem,
  solution: Solution,
  traction: Traction,
  moat: Moat,
  closeask: CloseAsk,
};

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

export const PitchVideo: React.FC = () => {
  const timing = linearTiming({ durationInFrames: CROSSFADE });
  let offset = 0;
  const narration = SCENE_ORDER.map((key, i) => {
    const base = offset;
    offset += SCENE_DURATIONS[key] - (i < SCENE_ORDER.length - 1 ? CROSSFADE : 0);
    return (
      <Sequence key={`a-${key}`} from={base} durationInFrames={AUDIO_DURATIONS[key]}>
        <Line file={AUDIO_FILES[key]} frames={AUDIO_DURATIONS[key]} />
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
      <PitchSubtitles />
    </AbsoluteFill>
  );
};
