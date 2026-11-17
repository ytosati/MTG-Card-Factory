# Design direction

The visual direction of the Card Factory interface. `src/styles/tokens.css`
carries every value named here; screen tasks follow this file, and a change of
direction changes this file first (specs/plan.md, section 16.9). The rules of
the Interface section of `specs/code-standards.md` are its limits.

Two gallery states show the direction in use:

- a form: `#/preview/request/filled` (and every other `#/preview/request/…` state);
- a list and a table: `#/preview/direction/card-list`.

## Character

Card Factory is a workbench for people who design, collect and build decks of
Magic: The Gathering cards for Commander. It is used in long sessions, so it
reads like a well-set reference, not like a product page: paper, ink, and one
violet for what the person does.

Its references are the ones a player already knows:

- the printed card: a title bar with the name and the mana cost, a type line,
  a text box, the power and toughness in the corner;
- a card page in a card database: the card text beside its image, the facts
  in ruled rows under it;
- a printed deck list: counts and names in a table, grouped by card type;
- editorial and reference books: serif titles, small capitals over columns,
  rules instead of boxes.

Three ideas hold it together:

1. **The card speaks in serif, the tool in sans.** Card names, rules text and
   screen titles use the serif; labels, controls, data and help use the sans.
2. **Rules, not boxes.** Content sits on the paper and is divided by
   horizontal rules. A box is kept for things that are a single object: a
   control, a message, the card text panel.
3. **Only cards are physical.** Card-shaped areas have the rounded corners of
   a printed card and are the only objects that cast a shadow. Everything else
   is flat ink on paper.

## Light, on purpose

The interface has one light scheme: warm paper (`--color-background`), a
lighter surface for controls and the card text (`--color-surface`) and near-black
ink (`--color-text`).

- Card text is read like print, and the serif rules text on paper reads like a
  card's own text box.
- Card art, which the person judges for color, shows truest on a neutral, light
  ground; a dark ground makes every image look brighter than it prints.
- Print sheets and the PDF are white paper; the screen that prepares them
  matches what comes out.
- One scheme keeps every contrast pair checked once.

A dark scheme is not part of the direction. The color tokens are named by role
(paper, surface, ink, rule, accent), so a later dark scheme would be one more
block of values in `tokens.css`, decided and checked as its own change.

## Type

### Families

Installed fonts only, chosen per system, until the bundled family below is
approved.

| Token | Role | Stack (first match wins) |
|---|---|---|
| `--font-display` | screen titles (`h1`, `h2`), card names | Iowan Old Style (macOS), Palatino Linotype (Windows), Palatino, Book Antiqua, URW Palladio L / P052 (Linux), Georgia |
| `--font-card` | the card's own text: name, type line, rules text, power and toughness | same as `--font-display` |
| `--font-ui` | labels, controls, data, help, messages | Segoe UI Variable Text, Segoe UI (Windows), the Apple system font, Helvetica Neue, Roboto, Noto Sans, Liberation Sans, Arial |
| `--font-mono` | setting names, file paths, a cost that is not written in symbols | ui-monospace, Cascadia Mono, SF Mono, Consolas, Liberation Mono |

The serifs of the stack share the Palatino skeleton (a calligraphic old style
close to the Plantin of printed cards), so the screens keep their voice on
every system. Numbers in data use `font-variant-numeric: tabular-nums`, so
columns of counts and tokens line up.

### Scale

| Token | Size | Use |
|---|---|---|
| `--font-size-h1` | 2.25rem | the one screen title; serif, regular weight |
| `--font-size-h2` | 1.5rem | sections of a screen; serif, regular weight |
| `--font-size-card-name` | 1.5rem | the card name in the card text panel; serif, bold |
| `--font-size-figure` | 1.75rem | a single large figure (sizes on Setup); serif |
| `--font-size-lead` | 1.0625rem | the summary under the title; card names in lists |
| `--font-size-card-text` | 1.0625rem | rules text; serif |
| `--font-size-h3` | 1.0625rem | sub-sections; sans, semibold |
| `--font-size-label` | 1.0625rem | the label of a form row; sans, bold |
| `--font-size-body` | 1rem | body text, labels, controls |
| `--font-size-small` | 0.875rem | hints, type lines in lists, secondary columns |
| `--font-size-caption` | 0.75rem | rubrics (column names, group names) and tags |

Weights: `--font-weight-regular` (400) for serif titles, running text and
the names of choices in a row, `--font-weight-strong` (600) for the names of
choices with a meaning, column names and the labels of single fields,
`--font-weight-bold` (700) for card names in title positions, the label of a
form row, mana symbols and totals. A form row reads from its label (larger,
bold) to its option names (semibold) to their meanings (small, muted).

Line heights: `--line-height-tight` (1.15) for titles, `--line-height-snug`
(1.35) for labels, list rows and table cells, `--line-height-body` (1.5) for
running text.

**Rubrics** name a column or a group: `--font-size-caption`, semibold,
uppercase, `--letter-spacing-rubric`, muted ink. They are used only over table
columns, for group rows and for the labels of a ledger, never for a sentence.

### Pending decision: a bundled serif

Proposed, not added. Until it is approved the stacks above stay.

| | |
|---|---|
| Family | Source Serif 4 (Adobe, Frank Grießhammer) |
| License | SIL Open Font License 1.1 (free to bundle and redistribute with the application) |
| Files | four static WOFF2 files: Regular 400, Semibold 600, Bold 700, Italic 400 |
| Subset | Latin: English and Portuguese (Brazil) letters, curly quotes, the em dash of type lines and the minus sign of loyalty costs (U+2212) |
| Size | estimated 25 to 35 KB per file, about 120 KB in all; measured when added |
| Replaces | the first entry of `--font-display` and `--font-card`; the sans and mono stacks stay installed fonts |

Why: the installed serifs differ in width between Windows, macOS and Linux, so
card names wrap at different points; one bundled family makes titles, card
names and rules text the same on every system. It is drawn for reading at text
sizes and holds up at title sizes, has tabular figures, and its italic serves
reminder and flavor text. The files would live under `src/assets/fonts/`, be loaded with
`@font-face` and `font-display: swap`, and be served by the application
(spec RN-33). Alternative with the same license and role: Literata
(TypeTogether).

## Space and density

A 4px rhythm: `--space-1` (0.25rem) to `--space-16` (4rem).

| Between | Space |
|---|---|
| a label and its control | `--space-2` |
| choices in a row | `--space-3`, plus `--space-2` of padding inside each choice for its hover tint |
| the name and the meaning of an option row | `--space-4` |
| rows of a ruled form | `--space-6` above and below, a hairline between |
| a title and the first content | `--space-8` |
| sections of a screen (`h2`) | `--space-10` above |
| the screen and the window edge | `--space-6` (wide), `--space-4` (narrow) |

Density follows the content. Forms are generous (`--control-height`, 2.5rem,
for every control). Lists and tables are compact: a table row is
`--row-height` (2.75rem), a list row is as tall as its thumbnail plus
`--space-3` above and below.

### Widths and layout

- `--content-width` (72rem): the axis shared by the header and every screen.
  Content is left-aligned on it; nothing is centered in the middle of the
  window.
- `--measure-column` (48rem): the default width of anything inside a screen;
  reading screens (Status, Setup, Result) are one column of this width.
- `--measure-wide` (62rem): forms, lists and tables, which opt in.
- `--measure-prose` (65ch): the longest line of running text, hints included.
- Breakpoints are container queries on the application (`.app`) or the
  gallery frame: **wide** from 56rem, where a form takes its two columns;
  **narrow** up to 40rem for lists and tables, 32rem for page padding. The
  layout works at 360px with no horizontal scrolling.

## Color

| Token | Value | Role |
|---|---|---|
| `--color-background` | #f4f1ea | the paper |
| `--color-surface` | #fffdf8 | controls, the card text panel |
| `--color-sunken` | #ece8df | wells: empty image areas, disabled controls, tags, code |
| `--color-row-hover` | #efebe3 | the row under the pointer in a table |
| `--color-text` | #1f1b16 | ink (15.2:1 on paper) |
| `--color-text-muted` | #57514a | secondary text (6.9:1 on paper, 6.4:1 on sunken) |
| `--color-border` | #ddd7cc | hairline rules; decoration only |
| `--color-border-control` | #8b8478 | edges of fields and choices (3.3:1 on paper, 3.6:1 on surface) |
| `--color-rule-strong` | #1f1b16 | the ink rule that opens a form, a list or a table |

Contrast meets WCAG 2.1 AA (spec RN-49): text 4.5:1 or more, control edges and
meaningful marks 3:1 or more. A hairline (`--color-border`) never is the only
edge of a control.

### The accent

`--color-accent` (#5b2a86, 8.8:1 on paper, white text on it 9.9:1) is the one
accent. It is a solid color, used only where the person acts or has chosen:

- the primary action of a screen (the filled button), links and quiet
  actions;
- keyboard focus (`--focus-ring-color`, a lighter violet of the same family,
  3px with a 2px offset). Its contrast holds because of the offset: the ring
  is drawn on the paper or a surface (3.8:1 and 4.2:1), never on the accent
  button it surrounds, where it would nearly vanish;
- the current place: the current screen in the header (a 2px bar on the
  header rule), the running step of a job;
- selection: the chosen option (the native radio or check in the accent and
  the option's name in the accent), the ring around a chosen mana symbol, a
  favorite mark, text selection;
- the product mark beside the name in the header.

It is never a background for a section, a heading color, a decoration or a
gradient. Hover on a field darkens its edge to muted ink and hover on a choice
tints it with `--color-row-hover`, never with the accent, so the accent always
means "chosen" or "act here".

### Tones and card colors

- Danger, notice and success each have a surface, a text and a border token;
  their text keeps 7:1 or more on their surface. A tone always comes with an
  icon and words, never color alone.
- Mana colors (`--color-mana-*`) fill mana symbols and tint empty card-shaped
  areas with the card's colors: one color its fill, two or more the gold of a
  multicolored frame (`--color-mana-multi`), colorless the generic fill. A
  tinted area keeps its control-colored outline and an inner line
  (`--color-card-inner-line`), like the edge of a card's art box; the colors
  are also in the cost, so the tint is never the only sign.
- Rarity colors (`--color-rarity-*`) fill the small rarity mark only; the
  rarity is always written beside it.

## Shape and depth

- `--radius` (4px): controls, the hover tint of a choice, the card text panel.
- `--radius-small` (2px): messages, tags, inline code.
- `--radius-card` (4.76% / 3.41%): every card-shaped area. It is the 3 mm corner
  of a 63 × 88 mm card in percentages, so a thumbnail and a full image are
  rounded alike. Card-shaped areas keep `--card-aspect-ratio` and show the
  whole image (spec RN-44).
- No pill shapes. Circles are only for mana symbols and step markers.
- `--shadow-card` belongs to card-shaped areas that hold an image. An empty
  card area is flat, outlined with `--color-border-control`, so it does not
  pretend to be a card; it may be tinted with the card's colors (see "Tones
  and card colors"). `--shadow-raised` is reserved for layers above the
  page (a menu, a dialog), with `--z-overlay`.
- Mana symbols are drawn as on a printed cost: the figure or letter in the
  card serif, bold, on its color, with the small ink offset of print
  (`--mana-symbol-offset`, one pixel down and to the left). This is a printed
  mark, not depth. Colored symbols have no edge; white, colorless and generic
  keep a hairline edge in `--color-mana-edge`, because their fill is close to
  the paper.

## Lists and tables

The shape of every collection of cards: the Library, Versions, Collection,
Decks, Extras and Print.

**A list of saved cards** is a list of ruled rows under an ink rule, with no
box per item. Each row, from left to right:

1. a card-shaped thumbnail, `--card-thumb-width` (3rem) wide, with the card
   corner and shadow; without an image, the flat outlined area tinted with the
   colors of the card's cost, and the words "No image" for assistive
   technology;
2. the card name (serif, bold, `--font-size-lead`) and, under it, the type line
   (sans, small, muted);
3. the mana cost as compact symbols (`--mana-symbol-size-compact`), in its own
   column so costs line up; the name column stops at
   `--card-list-identity-width` (26rem), so on a wide screen the cost stays
   near the name, as on a card's title bar;
4. the rarity: a small diamond in the rarity color and the word;
5. the marks, aligned right: a tag for a custom art version ("Art version 2":
   caption size, sunken, outlined, `--radius-small`) and the favorite star in
   the accent, with "Favorite" as hidden text.

The card name is the link to the card; a row whose name is a link gets
`--color-row-hover`. On a narrow screen the row folds into two lines: name and
cost on the first, rarity and marks on the second (one area, the rarity at its
start and the marks at its end, so every name wraps at the same width), the
thumbnail beside both.

A grid of card images (images only, name under each) is a second view of the
same list for browsing art; it uses the same card-shaped area, never a
different crop.

**A table** (deck list, usage, print queue) is a printed table:

- an ink rule above the column names; the column names are rubrics; a rule in
  `--color-border-control` under them; hairlines between rows; an ink rule
  above the total, which is bold;
- no outer box, no zebra stripes; the row under the pointer takes
  `--color-row-hover`, so the eye keeps its line across a wide row;
- numbers right-aligned and tabular; names in the serif at regular weight
  (dense rows), costs as compact symbols that never wrap;
- groups (Creatures, Planeswalkers) as a group row with a rubric and the
  count in parentheses, in the order a deck list prints them;
- the first and last columns, and the group rows, touch the rule ends (no
  outer padding);
- on a narrow screen secondary columns fold under the name (the type line
  becomes a second line of the name cell) instead of scrolling sideways, the
  count column narrows to `--table-count-width-narrow` and names drop to the
  body size, so a row stays one name line and one type line.

**A row of facts** (Status values, data sources, comparables) is a ruled
definition list: the term muted on the left, the value in ink on the right;
stacked on a narrow screen.

**The card display** (Result) follows a card page: the card image (card-shaped,
`--card-image-width`) beside the card text panel, stacked on a narrow screen.
The card text panel keeps the card's own structure: title bar (name in serif
bold, mana cost at the right), type line on a sunken band (serif bold), text
box (serif, `--font-size-card-text`, one paragraph per line, at most
`--measure-prose`), and a foot with the artist credit and the power and
toughness in an ink box at the right. The facts about the card follow under it
as `h2` sections with ruled rows.

## Forms

- A form opens with an ink rule and is a column of rows divided by hairlines;
  there is no panel around it.
- **Wide** (container 56rem or more): each row has two columns, the label and
  its hint in the left column (`--form-label-width`, 14rem), the controls in
  the right (`--form-controls-width`, 46rem). The action row repeats the grid,
  so the primary button lines up with the controls.
- **Narrow**: the label, then the hint, then the controls, in one column.
- The label of a row is sentence case, bold, ink, at `--font-size-label`; the
  labels of single fields inside the advanced options are semibold at body
  size. A hint is small, muted and linked to its control with
  `aria-describedby`.
- Required fields are named in the summary under the screen title, and each
  required control carries `aria-required` where its role allows it; labels
  keep their plain names.
- Text fields and text areas: surface, `--color-border-control` edge,
  `--radius`, at least `--control-height` tall; hover darkens the edge to muted
  ink; an invalid field takes the danger edge and a message under it in danger
  text.
- **Choices in a row** (colors, language, card types) sit on the paper with
  no box: the native checkbox or radio, then the name; colors carry their mana
  symbol between the two. Chosen: the native control checked in the accent,
  the name in the accent, and a chosen mana symbol ringed in the accent
  (`--selection-ring-width`). The native control stays visible, so the state
  never depends on color alone.
- **Choices with a meaning** (power level, generation effort) are ruled rows:
  the radio and the name in semibold in a column of `--option-name-width`
  (7rem), the one-line meaning beside it in muted small text, a hairline
  between rows, no edge and no fill. On a phone (container up to 32rem) the
  meaning folds under the name. The whole row is the click target. Chosen:
  the radio and the name in the accent.
- Hover tints a choice or a row with `--color-row-hover`. Keyboard focus rings
  the whole choice or row (`:has(input:focus-visible)`), not the small native
  control inside it.
- On a narrow screen (container up to 40rem) choices and the disclosure are at
  least `--touch-target` (2.75rem) tall; the primary button always is.
- A locked form (a generation running) keeps every value readable: fields
  turn sunken with a hairline edge, names turn muted, chosen ones keep a
  quieter accent.
- Advanced options hide behind a disclosure button in the accent with a
  chevron that turns; on a wide screen the disclosure sits in the label column.
- The action row closes the form with an ink rule. One filled accent button
  per form; secondary actions are quiet (accent text, no fill). Progress and
  the running step appear beside the button; a failure appears under it.
- While a card is generated step by step, the action row shows the card that
  is coming: an empty card-shaped area (`--card-placeholder-width`) tinted
  with the requested colors, the running step written under it ("Step 3 of 6:
  Draft"), and the list of steps beside it.

## Notices and states

- **Messages** (`Notice`): tinted surface, a 1px border in the tone,
  `--radius-small`, an icon and words. Danger is an alert; notice and success
  are a status. A message that leads to an action holds it (a link to Status, a
  button to edit the request).
- **Loading**: a short sentence in a status region ("Checking the card
  database…"); a job shows its steps with the running one marked, or a bar with
  quarter marks when only a fraction is known. No spinners on their own and no
  skeleton screens.
- **Empty**: say what is missing and how to fill it, in a muted sentence where
  the list would be ("No saved cards yet. Generate a card on Request."). No
  illustration.
- **Error while reading**: a danger message with the cause and a "Try again"
  button, in place of the content.
- A whole-application state (stopped, readiness unknown) is a full-width bar
  under the header, on the same content axis.
- The running steps of a job are a vertical list of markers joined by a line:
  done steps and their line in the accent, the current step an accent ring with
  its name in the accent, waiting steps in muted ink.

## Motion

Few, short and only to explain a change of state (spec RN-49; code standards,
"Shapes and motion").

| Token | Value | Use |
|---|---|---|
| `--motion-duration-fast` | 120ms | color, edge and fill changes on hover, choice and press |
| `--motion-duration-medium` | 200ms | a disclosure chevron, a progress bar, a message appearing |
| `--motion-easing-out` | cubic-bezier(0.2, 0, 0, 1) | everything that settles into place; no overshoot |
| `--motion-easing-in-out` | cubic-bezier(0.4, 0, 0.2, 1) | a value moving between two states |
| `--motion-press-offset` | 1px | a pressed button moves down |
| `--motion-enter-offset` | 0.25rem | a message rises into place while it fades in |

- Allowed: hover and choice transitions, a pressed button, a message or a new
  row appearing, a step being reached, a progress bar filling, a disclosure
  opening.
- Hover styles apply only under `(hover: hover) and (pointer: fine)`, so a
  tap leaves no tint behind. A table row's tint appears at once when the
  pointer enters and fades when it leaves, so the tint never lags behind the
  pointer.
- Not allowed: bounces, springs, scroll-triggered animation, looping
  decoration, page transitions, anything that delays reaching the content.
- Under `prefers-reduced-motion: reduce` one rule in `tokens.css` sets every
  duration and offset to zero; the gallery's "Reduced motion" switch does the
  same inside its frame.

## Accessibility

- Contrast as listed under Color; check new pairs before adding a token.
- Focus: the global `:focus-visible` ring on every control, never removed
  without a replacement; the ring is drawn inside the header links so the
  header does not clip it, and around the whole choice or row for checkboxes
  and radios. Its 2px offset keeps it on the paper, which is what gives it
  its contrast.
- Every control is native (button, input, select, link) and reachable with the
  keyboard; a larger click target is made with a pseudo-element on the label,
  never with a click handler on a `div`.
- One `h1` per screen; headings do not skip levels; tables have column headers
  and row headers (`scope`), lists of cards are `ul`.
- Mana costs are read as words; marks drawn as shapes (rarity, favorite, tone
  icons) have their meaning in text beside them or hidden for assistive
  technology.
- Images keep their space (width and height or an aspect ratio) and have an
  `alt` that names the card and says it is the art.

## What to avoid

- A centered column of bordered cards; a box around every section; nested
  boxes.
- A hero, a tagline, a gradient banner or any marketing copy.
- Purple-to-blue or any decorative gradient, glow, glass, blur or neon; the
  accent as a background for decoration.
- Pill-shaped buttons, fields or badges; a badge on everything.
- Emoji, stock illustration, generated images outside card art.
- A neutral grey system page with no type hierarchy.
- Cropping, stretching or re-coloring card images; a card area that is not the
  shape of a card.
- Spinners on their own, skeleton screens, bouncy or decorative motion.
- Fonts, icons or styles loaded from outside the application.
