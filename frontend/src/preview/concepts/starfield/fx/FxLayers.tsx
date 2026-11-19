// Concept E "Starfield" (tasks.md T251): several pixelfx effects stacked on one point, played together.
import type { CSSProperties } from "react";

import type { FxLayer } from "./effects";
import { PixelFx } from "./PixelFx";

type FxLayersProps = {
  layers: readonly FxLayer[];
  /** Screen pixels per effect pixel for every layer; a layer's own scale multiplies it. */
  scale?: number;
  mode?: "loop" | "once";
  playKey?: string | number;
  className?: string;
  style?: CSSProperties;
};

/** A zero-size anchor: every layer is centred on it, so the caller places the point where the effects meet. */
export function FxLayers({ layers, scale = 3, mode, playKey, className, style }: FxLayersProps) {
  return (
    <span aria-hidden="true" className={className} style={{ position: "absolute", width: 0, height: 0, pointerEvents: "none", ...style }}>
      {layers.map((layer, index) => {
        const size = scale * (layer.scale ?? 1);
        return (
          <PixelFx
            key={index}
            effect={layer.effect}
            options={layer.options}
            width={layer.width}
            height={layer.height}
            origin={layer.origin}
            speed={layer.speed}
            scale={size}
            mode={mode}
            playKey={playKey}
            style={{
              position: "absolute",
              left: (layer.dx ?? 0) - (layer.width * size) / 2,
              top: (layer.dy ?? 0) - (layer.height * size) / 2,
            }}
          />
        );
      })}
    </span>
  );
}
