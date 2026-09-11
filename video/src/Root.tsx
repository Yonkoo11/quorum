import React from "react";
import { Composition, registerRoot } from "remotion";
import { MainVideo } from "./MainVideo";
import { SocialClip, SOCIAL_DURATION, SOCIAL_FPS, SOCIAL_H, SOCIAL_W } from "./SocialClip";
import { FPS, H, TOTAL_FRAMES, W } from "./constants";

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Main" component={MainVideo} durationInFrames={TOTAL_FRAMES} fps={FPS} width={W} height={H} />
    <Composition
      id="Social"
      component={SocialClip}
      durationInFrames={SOCIAL_DURATION}
      fps={SOCIAL_FPS}
      width={SOCIAL_W}
      height={SOCIAL_H}
    />
  </>
);

registerRoot(RemotionRoot);
