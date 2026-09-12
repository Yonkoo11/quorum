import React from "react";
import { Composition, registerRoot } from "remotion";
import { MainVideo } from "./MainVideo";
import { SocialClip, SOCIAL_DURATION, SOCIAL_FPS, SOCIAL_H, SOCIAL_W } from "./SocialClip";
import { FPS, H, TOTAL_FRAMES, W } from "./constants";
import { UiLaunch } from "./ui/UiLaunch";
import { UI_FPS, UI_H, UI_TOTAL_FRAMES, UI_W } from "./ui/constants";

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
    <Composition id="UiLaunch" component={UiLaunch} durationInFrames={UI_TOTAL_FRAMES} fps={UI_FPS} width={UI_W} height={UI_H} />
  </>
);

registerRoot(RemotionRoot);
