import React from "react";
import { Composition } from "remotion";
import { PithVerticalVideo } from "./PithVerticalVideo";

// Default fallback manifest when rendering
import defaultManifest from "../../public/audio/timestamps-developer.json";

export const Root: React.FC = () => {
  const durationInFrames = Math.max(1800, defaultManifest.total_frames || 1800);

  return (
    <Composition
      id="PithDailyBrief"
      component={PithVerticalVideo}
      durationInFrames={durationInFrames}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{
        manifest: defaultManifest,
      }}
    />
  );
};
