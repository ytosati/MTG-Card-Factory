// Goblin crew of the forge scene, drawn facing right (tasks.md T251, concept D "Forge").
import { PixelCanvas, type PixelRows } from "./pixelArt";

type Part = readonly [PixelRows, number, number];

function compose(width: number, height: number, parts: readonly Part[]): PixelRows {
  const canvas = new PixelCanvas(width, height);
  for (const [art, x, y] of parts) canvas.stamp(art, x, y);
  return canvas.toRows();
}

// The engineer: brass goggles pushed up on the brow, one long ear, a hooked nose.
const ENGINEER_HEAD: PixelRows = [
  ".......kkkkkk.....",
  ".....kkLLSSSSk....",
  "....kLLSSSSSSsk...",
  "k..kbbkkkkkkkkkk..",
  "kk.kbkDgGgkDgGgk..",
  "kSkkbkg..gkg..gk..",
  "kLSkbkg..gkg..gk..",
  ".kLSSkDggDkDggDk..",
  ".kaSLSkkkkSkkkkSk.",
  "..kaSSSSSSSSsSSSLk",
  "...kaSSSSSSSSSSSLLk",
  "....kasSSSSkkkSSLLk",
  ".....kasSSkeekkSsk.",
  "......kassSkkkSsk..",
  ".......kkaaaaakk...",
  ".........kkkkk.....",
];

/** Eyes seen through the goggle lenses, at (7, 5) of the head: open, then shut. */
const ENGINEER_EYES_OPEN: PixelRows = ["WC...WC", "Ck...Ck"];
const ENGINEER_EYES_SHUT: PixelRows = ["cc...cc", "kk...kk"];

// Shirt, leather apron with a gold rivet, boots; the front arm is a separate part.
const ENGINEER_BODY: PixelRows = [
  ".....kkkkkkkk.....",
  "....kJJIIIIbbk....",
  "...kJJIIIIkbBnk...",
  "..kSkJIIIkbBBnk...",
  "..kSkIIIIkbBgBk...",
  "..kLSkIIIkbBBBk...",
  "..kLSkIIIkbBBBk...",
  "...kkkllllllllk...",
  "....kiIIkkkiIIk...",
  "....kiIk...kiIk...",
  "...kllbk..kllbk...",
  "...kkkkk..kkkkkk..",
];

// Front arm hanging down, the hammer held head-down.
const ENGINEER_ARM_REST: PixelRows = [
  "kkk...",
  "kSSk..",
  "kSSk..",
  ".kSLk.",
  ".kSLk.",
  "..kBk.",
  "..kBk.",
  ".kJIIk",
  ".kIiik",
  "..kkkk",
];

// Hammer cocked back over the shoulder (drawn behind the head), then brought down in front.
const ENGINEER_ARM_RAISED: PixelRows = [
  "kkkkkkk..",
  "kJJIIJk..",
  "kIiiiIk..",
  ".kkBkk...",
  "...kBk...",
  "...kBk...",
  "...kBk...",
  "....kBk..",
  "....kBk..",
  "....kBk..",
  "....kBk..",
  "....kLSk.",
  "....kSSk.",
  "....kSSk.",
  ".....kSk.",
  ".....kSk.",
  "......kk.",
];

const ENGINEER_ARM_STRIKE: PixelRows = [
  ".......kkkk",
  "k......kJIk",
  "kSk....kIik",
  ".kSSkkkkIik",
  "..kSLBbbJIk",
  "...kkkkkkkk",
];

const ENGINEER_SEAT: PixelRows = [
  ".....kkkkkkkk.....",
  "....kJJIIIIbbk....",
  "...kJJIIIIkbBnk...",
  "..kSkJIIIkbBBnk...",
  "..kSkIIIIkbBgBkk..",
  "..kLSkIIkbBBBkLSk.",
  "...kLSkkllllllkSk.",
  "....kkiIIIIIIIiIk.",
  "....kiIIkkkkkiIIk.",
  "...kllbbk...kllbk.",
  "...kkkkkk...kkkkk.",
];

const STOOL: PixelRows = [
  "kkkkkkkkkkkk",
  "kGgggggggDDk",
  "kDDDDDDDDddk",
  ".kbk....kbk.",
  ".kbk....kbk.",
  ".kbk....kbk.",
  ".kkk....kkk.",
];

/** Engineer at work: standing with the hammer down, raised, then striking. */
export const ENGINEER_STAND: PixelRows = compose(24, 28, [
  [ENGINEER_BODY, 2, 15],
  [ENGINEER_HEAD, 2, 0],
  [ENGINEER_EYES_OPEN, 9, 5],
  [ENGINEER_ARM_REST, 13, 17],
]);
export const ENGINEER_RAISE: PixelRows = compose(24, 28, [
  [ENGINEER_ARM_RAISED, 0, 0],
  [ENGINEER_BODY, 2, 15],
  [ENGINEER_HEAD, 2, 1],
  [ENGINEER_EYES_OPEN, 9, 6],
]);
export const ENGINEER_STRIKE: PixelRows = compose(24, 28, [
  [ENGINEER_BODY, 2, 15],
  [ENGINEER_HEAD, 2, 1],
  [ENGINEER_EYES_OPEN, 9, 6],
  [ENGINEER_ARM_STRIKE, 12, 13],
]);

/** Engineer asleep on a stool; the second frame is the breath out, a pixel lower. */
function dozing(drop: number, eye: PixelRows): PixelRows {
  return compose(24, 30, [
    [STOOL, 4, 23],
    [ENGINEER_SEAT, 2, 13],
    [ENGINEER_HEAD, 3, 1 + drop],
    [eye, 10, 6 + drop],
  ]);
}
export const ENGINEER_DOZE_IN = dozing(0, ENGINEER_EYES_SHUT);
export const ENGINEER_DOZE_OUT = dozing(1, ENGINEER_EYES_SHUT);
export const ENGINEER_DOZE_PEEK = dozing(0, ENGINEER_EYES_OPEN);

// The arcane sage: one bushy unibrow hides the eyes, a jagged beard, a gold earring.
const SAGE_HEAD: PixelRows = [
  ".....kkkkkk.......",
  "....kRPPRRrk......",
  "...kRPPRRRRrk.....",
  "..kRPRRRRRRRrk....",
  "..kRPRRRRRRRRrk...",
  ".kRPRRkkkkkkkRrk..",
  "kkRPRkSSSSLLLkRk..",
  "kSkRkUUUUUUUUUUk..",
  "kLSkUUUUUUUUUUUUk.",
  ".kLSkuUuUuuUuUSLk.",
  ".kgkSSSSSSSSSSSLLk",
  "..kRkaSSSSSSSSLLk.",
  "..kRkUUSSSSSSSkk..",
  "..kRkUUUUUUUUUk...",
  "...kkUUuUUUuUUk...",
];

const SAGE_BEARD: PixelRows = [
  "kUUUUUUUUUk",
  "kuUUUUUUUuk",
  ".kuUuUUuUk.",
  "..kuUkuUk..",
  "...kk.kk...",
];

const SAGE_ROBE: PixelRows = [
  "......kkkkkk......",
  ".....kRPPRRRk.....",
  "....kRPPRRRrrk....",
  "....kRPRRRrrrk....",
  "...kRPRRRgrrrrk...",
  "...kRPRRRgRrrrk...",
  "...kRPRRRgRrrrk...",
  "..kRPRRRRgRrrrrk..",
  "..kRPRRRRgRRrrrk..",
  "..kRPRRRRgRRrrrk..",
  ".kRPRRRRRgRRrrrrk.",
  ".kkkkkkkkkkkkkkkk.",
];

// Closed scroll held at the chest.
const SAGE_HANDS_SCROLL: PixelRows = [
  "..kk....",
  ".kSSk...",
  "kgkkkkgk",
  "kGeeeeDk",
  "kgUUUUDk",
  ".kSLk...",
  "..kk....",
];

// Open scroll held up to the face; "x" glyphs glow on the parchment.
const SAGE_HANDS_READ: PixelRows = [
  ".....kkkkkk",
  "....kGeeeeD",
  "...kSkexeXe",
  "...kSkeXexe",
  "..kSLkexXee",
  "..kSkkeeXxe",
  "...kk.kgggD",
  "......kkkkk",
];

export const SAGE_IDLE: PixelRows = compose(24, 28, [
  [SAGE_ROBE, 2, 15],
  [SAGE_HEAD, 2, 0],
  [SAGE_BEARD, 6, 14],
  [SAGE_HANDS_SCROLL, 11, 16],
]);
export const SAGE_READ: PixelRows = compose(24, 28, [
  [SAGE_ROBE, 2, 15],
  [SAGE_HEAD, 2, 1],
  [SAGE_BEARD, 6, 15],
  [SAGE_HANDS_READ, 12, 9],
]);
/** Same pose a pixel lower: the sage nods along the lines. */
export const SAGE_READ_NOD: PixelRows = compose(24, 28, [
  [SAGE_ROBE, 2, 15],
  [SAGE_HEAD, 2, 2],
  [SAGE_BEARD, 6, 16],
  [SAGE_HANDS_READ, 12, 9],
]);

// The operator: a flame-red mohawk, a wide grin, denim overalls.
const OPERATOR_HEAD: PixelRows = [
  "....k.k.k.k.......",
  "...kQkQkQkQk......",
  "...kqQqQqQqQk.....",
  "..kkqqqqqqqqk.....",
  "..kLLSSqqqSSSkk...",
  "k.kLSSSSSSSSSssk..",
  "kkkLSSSSSSSSSSsk..",
  "kSkSSSSSSSkkkSSSk.",
  "kLSSSSSSSSkykSSSk.",
  ".kLSSSSSSSkkkSSSLk",
  ".kaSSSSSSSSSSSSLLLk",
  "..kaSSSSSSSSSSSSLLk",
  "...kasSkkkkkkkkkk..",
  "....kaSkeeekeeek...",
  ".....kasSkkkkkkk...",
  "......kkkkkkk......",
];

const OPERATOR_BODY: PixelRows = [
  ".....kkkkkkk......",
  "....kJJIgkOOk.....",
  "...kJJOOgOOOOk....",
  "...kJOOOOOOOok....",
  "...kSOOOgOOOok....",
  "...kSOOOOOOOok....",
  "...kLkOOOOOOok....",
  "....kkoOOOOOok....",
  "....koOOkkoOOk....",
  "....koOk..koOk....",
  "...kllbk.kllbk....",
  "...kkkkk.kkkkkk...",
];

// Both hands on the lever grip, up then pulled down.
const OPERATOR_ARMS_UP: PixelRows = [
  "......kkk",
  ".....kSLk",
  "....kSSk.",
  "...kSSk..",
  "..kSSk...",
  "..kSk....",
  "..kk.....",
];
const OPERATOR_ARMS_DOWN: PixelRows = [
  "kkk......",
  "kSSkk....",
  ".kSSSkk..",
  "..kkSSSkk",
  "....kkSLk",
  "......kkk",
];

export const OPERATOR_READY: PixelRows = compose(24, 28, [
  [OPERATOR_BODY, 2, 16],
  [OPERATOR_HEAD, 2, 0],
  [OPERATOR_ARMS_UP, 13, 12],
]);
export const OPERATOR_PULL: PixelRows = compose(24, 28, [
  [OPERATOR_BODY, 2, 16],
  [OPERATOR_HEAD, 2, 1],
  [OPERATOR_ARMS_DOWN, 13, 18],
]);
/** Where the operator's hands meet the lever grip, relative to the sprite, per pose. */
export const OPERATOR_GRIP = { ready: { x: 20, y: 13 }, pull: { x: 20, y: 21 } } as const;
