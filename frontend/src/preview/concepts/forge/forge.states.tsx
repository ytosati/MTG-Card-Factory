// Preview states of concept D (Forge), the refined Nocturne direction. Task T251.
import type { PreviewState } from "../../types";
import { MachineBench } from "./MachineBench";
import { SymbolSheet } from "./SymbolSheet";

export const forgeStates: PreviewState[] = [
  { id: "machine", name: "The forge", render: () => <MachineBench /> },
 { id: "symbols", name: "Mana symbols", render: () => <SymbolSheet /> }];
