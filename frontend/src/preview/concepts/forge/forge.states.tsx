// Preview states of concept D (Forge), the refined Nocturne direction. Task T251.
import type { PreviewState } from "../../types";
import { SymbolSheet } from "./SymbolSheet";

export const forgeStates: PreviewState[] = [{ id: "symbols", name: "Mana symbols", render: () => <SymbolSheet /> }];
