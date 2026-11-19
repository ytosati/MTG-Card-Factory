# pixelfx (vendored)

Pixel art effects drawn in code, from https://github.com/patch-gg/pixelfx, copied at commit
`5294518ce7c72e48b6100a744596e0acf57f2826`. MIT License; see `LICENSE` in this folder.

## What is here

- `core/`: the library's `src/core`, unchanged.
- `fx/<category>/`: only the effect files the application uses, with their category's `_lib.js`, keeping their
  own headers.
- `fx/fire/brazier.js` is changed: a `prop` option (default true) leaves out the tripod, the bowl and the floor
  light. Its header says so.
- `fx/forge/` holds Card Factory's own effects, built on this library's toolkit and effect libraries. Each file's
  header says what it builds on.

The library's Patch Pixel font is not part of this copy.

## Notices carried over

**Hugo Duprez.** `core/sim.js` and the effects that say so at the top of their file adapt Sprite Fusion's
open-source pixel art VFX (https://www.spritefusion.com/pixel-art-vfx), Copyright (c) 2026 Hugo Duprez, MIT License.

**Hollow Crown.** `core/act.js` adapts how Hollow Crown plays its skills (poses on 12 fps steps, hit-stops, the
springy straw target), from https://github.com/rehan-remade/hollow-crown, Copyright (c) 2026 rehan-remade, MIT
License.
