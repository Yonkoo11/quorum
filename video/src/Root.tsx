import React from "react";
import { Composition, registerRoot } from "remotion";
import { MainVideo } from "./MainVideo";
import { FPS, H, TOTAL_FRAMES, W } from "./constants";

export const RemotionRoot: React.FC = () => (
  <Composition id="Main" component={MainVideo} durationInFrames={TOTAL_FRAMES} fps={FPS} width={W} height={H} />
);

registerRoot(RemotionRoot);
