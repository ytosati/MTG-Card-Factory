// @vitest-environment jsdom
// Concept E "Starfield" (tasks.md T251): parsing and accessible names of the mana symbols, and the color toggle.
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ManaPick } from "./ManaPick";
import { ManaCostSymbols, ManaSymbol } from "./ManaSymbol";
import { parseManaCost, parseManaSymbol, spokenSymbol } from "./manaSymbols";

afterEach(cleanup);

const spoken = (symbol: string) => {
  const parsed = parseManaSymbol(symbol);
  return parsed ? spokenSymbol(parsed) : null;
};

describe("mana symbols", () => {
  it("names every kind of symbol, ignoring case", () => {
    expect(spoken("{G}")).toBe("green mana");
    expect(spoken("{2}")).toBe("two generic mana");
    expect(spoken("{20}")).toBe("twenty generic mana");
    expect(spoken("{x}")).toBe("X mana");
    expect(spoken("{w/u}")).toBe("white or blue hybrid mana");
    expect(spoken("{2/G}")).toBe("two generic or green hybrid mana");
    expect(spoken("{G/P}")).toBe("Phyrexian green mana");
    expect(spoken("{C}")).toBe("colorless mana");
    expect(spoken("{T}")).toBe("tap");
    expect(spoken("{Q}")).toBe("untap");
  });

  it("rejects what is not a symbol", () => {
    expect(parseManaSymbol("{K}")).toBeNull();
    expect(parseManaSymbol("{G/2}")).toBeNull();
    expect(parseManaSymbol("{W/W}")).toBeNull();
    expect(parseManaCost("{2}{G}")).toEqual(["{2}", "{G}"]);
    expect(parseManaCost("2G")).toBeNull();
  });

  it("gives a symbol and a whole cost an accessible name", () => {
    render(
      <>
        <ManaSymbol symbol="{R/W}" />
        <ManaCostSymbols cost="{2}{G}{G}" />
      </>,
    );
    expect(screen.getByRole("img", { name: "red or white hybrid mana" })).toBeTruthy();
    expect(screen.getByRole("img", { name: "Mana cost: two generic mana, green mana, green mana" })).toBeTruthy();
  });

  it("toggles a color through its native checkbox", () => {
    const onChange = vi.fn();
    render(<ManaPick letter="G" checked={false} onChange={onChange} label="Green" />);
    fireEvent.click(screen.getByRole("checkbox", { name: "Green" }));
    expect(onChange).toHaveBeenCalledWith(true);
  });
});
