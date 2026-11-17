// Preview states of the Request screen: the generation fields, refusals and the running step.
// Details: specs/spec.md, RN-11, RN-50, RN-53 to RN-56, RN-58 and "Screens" (Request); specs/tasks.md, T168.
import { useState } from "react";
import type { ReactNode } from "react";

import type { ColorLetter, PowerLevel } from "../api/types";
import { requestCopy } from "../screens/request/copy";
import type { CardLanguage, GenerationEffort, GenerationStep } from "../screens/request/copy";
import { GenerationSteps, NO_ADVANCED_OPTIONS, RequestView } from "../screens/request/RequestView";
import type { AdvancedOptions, RequestFieldErrors, RequestProblem } from "../screens/request/RequestView";
import type { PreviewState } from "./types";

/** What a state starts with; the fields stay editable in the gallery. */
interface RequestFixture {
  idea: string;
  colors: ColorLetter[];
  colorless: boolean;
  power: PowerLevel | null;
  /** Medium when the spec gives no default effort. */
  effort: GenerationEffort | null;
  language: CardLanguage;
  advanced: AdvancedOptions;
  errors: RequestFieldErrors;
  refusedByServer: boolean;
  /** The running step, with whether art was requested; null when no generation runs. */
  running: { step: GenerationStep; withArt: boolean } | null;
  failure: RequestProblem | null;
}

const EMPTY: RequestFixture = {
  idea: "",
  colors: [],
  colorless: false,
  power: null,
  effort: "medium",
  language: "en",
  advanced: NO_ADVANCED_OPTIONS,
  errors: {},
  refusedByServer: false,
  running: null,
  failure: null,
};

const FILLED: RequestFixture = {
  ...EMPTY,
  idea: "A lantern keeper of the marsh who guides lost spirits home and grows stronger with each one.",
  colors: ["W", "B"],
  power: "medium",
  effort: "high",
};

// A fictional idea over the limit of 1,000 characters (RN-11).
const LONG_IDEA = "A clockwork heron that folds time around the pond it guards. ".repeat(17).trim();

function fixture(overrides: Partial<RequestFixture>): RequestFixture {
  return { ...EMPTY, ...overrides };
}

/** The Request view fed by a fixture; changes stay in the gallery and nothing is sent. */
function RequestPreview({ initial }: { initial: RequestFixture }) {
  const [state, setState] = useState(initial);
  const update = (next: Partial<RequestFixture>) => setState((previous) => ({ ...previous, ...next }));
  const progress: ReactNode =
    state.running !== null ? (
      <GenerationSteps step={state.running.step} withArt={state.running.withArt} colors={state.colors} />
    ) : null;

  return (
    <RequestView
      idea={state.idea}
      colors={state.colors}
      colorless={state.colorless}
      power={state.power}
      errors={state.errors}
      refusedByServer={state.refusedByServer}
      busy={state.running !== null}
      sending={false}
      progress={progress}
      failure={state.failure}
      controls={{
        effort: state.effort,
        language: state.language,
        advanced: state.advanced,
        onEffortChange: (effort) => update({ effort }),
        onLanguageChange: (language) => update({ language }),
        onAdvancedChange: (advanced) => update({ advanced }),
      }}
      onIdeaChange={(idea) => update({ idea })}
      onToggleColor={(letter) =>
        update({
          colorless: false,
          colors: state.colors.includes(letter)
            ? state.colors.filter((item) => item !== letter)
            : [...state.colors, letter],
        })
      }
      onToggleColorless={() => update({ colorless: !state.colorless, colors: [] })}
      onPowerChange={(power) => update({ power })}
      onSubmit={(event) => event.preventDefault()}
    />
  );
}

function preview(initial: RequestFixture): () => ReactNode {
  return () => <RequestPreview initial={initial} />;
}

function generating(step: GenerationStep, withArt = false): RequestFixture {
  return { ...FILLED, running: { step, withArt } };
}

export const requestStates: PreviewState[] = [
  { id: "empty", name: "Empty", render: preview(EMPTY) },
  { id: "filled", name: "Filled", render: preview(FILLED) },
  {
    id: "refused-field",
    name: "A refused field named",
    render: preview(
      {
        ...FILLED,
        idea: LONG_IDEA,
        errors: { idea: requestCopy.ideaTooLong(1_000) },
        refusedByServer: true,
      },
    ),
  },
  { id: "generating-design-intent", name: "Generating: design intent", render: preview(generating("design")) },
  { id: "generating-search", name: "Generating: search for related cards", render: preview(generating("search")) },
  { id: "generating-draft", name: "Generating: draft", render: preview(generating("draft")) },
  { id: "generating-validation", name: "Generating: validation", render: preview(generating("validation")) },
  { id: "generating-revision", name: "Generating: revision", render: preview(generating("revision")) },
  { id: "generating-art", name: "Generating: art", render: preview(generating("art", true)) },
  {
    id: "one-at-a-time",
    name: "Another generation is already running",
    render: preview({ ...FILLED, failure: { message: requestCopy.alreadyRunning, setting: null } }),
  },
  {
    id: "provider-refusal",
    name: "Provider refusal",
    render: preview(
      {
        ...FILLED,
        idea: "Captain Nemo at the helm of the Nautilus, sinking the warships that hunt the sea.",
        colors: ["U"],
        failure: { message: requestCopy.providerRefused, setting: null, refused: true },
      },
    ),
  },
  {
    id: "prefilled",
    name: "Prefilled from a card",
    render: preview(
      fixture({
        idea: "A squirrel that hoards acorns and spends them to grow its forest.",
        colors: ["G"],
        power: "casual",
        effort: "low",
      }),
    ),
  },
];
