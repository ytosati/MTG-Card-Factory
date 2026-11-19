// Concept D "Forge" (tasks.md T251): short sounds synthesized with the Web Audio API, and the mute setting.
import { useSyncExternalStore } from "react";

import type { ManaColor } from "../symbols/manaSymbols";

const MUTED_KEY = "cardfactory.sound.muted";

function readMuted(): boolean {
  try {
    return window.localStorage.getItem(MUTED_KEY) === "true";
  } catch {
    return false;
  }
}

let muted = typeof window === "undefined" ? false : readMuted();
const listeners = new Set<() => void>();

export function isMuted(): boolean {
  return muted;
}

export function setMuted(value: boolean): void {
  muted = value;
  try {
    window.localStorage.setItem(MUTED_KEY, String(value));
  } catch {
    // Storage may be blocked; the choice then lasts for this page only.
  }
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Whether sound is muted, kept in step with every other user of the store. */
export function useSoundMuted(): boolean {
  return useSyncExternalStore(subscribe, isMuted, isMuted);
}

type AudioContextClass = typeof AudioContext;

let context: AudioContext | null = null;
let noise: AudioBuffer | null = null;

/** The shared context, created on the first sound, which always follows a user gesture. */
function audio(): AudioContext | null {
  if (muted || typeof window === "undefined") return null;
  try {
    if (!context) {
      const Context = (window.AudioContext ??
        (window as unknown as { webkitAudioContext?: AudioContextClass }).webkitAudioContext) as AudioContextClass | undefined;
      if (!Context) return null;
      context = new Context();
    }
    if (context.state === "suspended") void context.resume().catch(() => undefined);
    return context;
  } catch {
    return null;
  }
}

function noiseBuffer(ctx: AudioContext): AudioBuffer {
  if (!noise) {
    noise = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
    const data = noise.getChannelData(0);
    for (let i = 0; i < data.length; i += 1) data[i] = Math.random() * 2 - 1;
  }
  return noise;
}

/** A gain node shaped as attack then exponential decay; the ramps from and to near zero avoid clicks. */
function envelope(ctx: AudioContext, start: number, attack: number, peak: number, decay: number): GainNode {
  const gain = ctx.createGain();
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(peak, start + attack);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + attack + decay);
  gain.connect(ctx.destination);
  return gain;
}

function tone(
  ctx: AudioContext,
  { type = "sine", from, to = from, start, attack = 0.005, peak, decay, glide = decay }: {
    type?: OscillatorType; from: number; to?: number; start: number; attack?: number; peak: number; decay: number; glide?: number;
  },
): void {
  const osc = ctx.createOscillator();
  osc.type = type;
  osc.frequency.setValueAtTime(from, start);
  if (to !== from) osc.frequency.exponentialRampToValueAtTime(to, start + glide);
  osc.connect(envelope(ctx, start, attack, peak, decay));
  osc.start(start);
  osc.stop(start + attack + decay + 0.05);
}

function hiss(
  ctx: AudioContext,
  { filter, frequency, to = frequency, q = 1, start, attack = 0.005, peak, decay }: {
    filter: BiquadFilterType; frequency: number; to?: number; q?: number; start: number; attack?: number; peak: number; decay: number;
  },
): void {
  const source = ctx.createBufferSource();
  source.buffer = noiseBuffer(ctx);
  const band = ctx.createBiquadFilter();
  band.type = filter;
  band.Q.value = q;
  band.frequency.setValueAtTime(frequency, start);
  if (to !== frequency) band.frequency.exponentialRampToValueAtTime(to, start + attack + decay);
  source.connect(band).connect(envelope(ctx, start, attack, peak, decay));
  source.start(start, Math.random() * 0.4);
  source.stop(start + attack + decay + 0.05);
}

/** Runs a sound only when audio is available and not muted; a failure is silent. */
function play(draw: (ctx: AudioContext, now: number) => void): void {
  const ctx = audio();
  if (!ctx) return;
  try {
    draw(ctx, ctx.currentTime + 0.01);
  } catch {
    // A sound is never worth an error on screen.
  }
}

const PICKS: Record<ManaColor, (ctx: AudioContext, now: number) => void> = {
  R: (ctx, now) => {
    hiss(ctx, { filter: "lowpass", frequency: 700, start: now, attack: 0.04, peak: 0.08, decay: 0.4 });
    [0, 0.05, 0.09, 0.16, 0.22, 0.3, 0.37].forEach((offset, index) => {
      hiss(ctx, { filter: "bandpass", frequency: 1800 + ((index * 937) % 2600), q: 3, start: now + offset, attack: 0.002, peak: 0.2, decay: 0.025 + (index % 3) * 0.01 });
    });
  },
  U: (ctx, now) => {
    tone(ctx, { from: 1500, to: 420, start: now, attack: 0.004, peak: 0.18, decay: 0.16, glide: 0.09 });
    tone(ctx, { from: 320, to: 170, start: now + 0.085, attack: 0.006, peak: 0.12, decay: 0.22, glide: 0.12 });
  },
  W: (ctx, now) => {
    [1, 2.76, 5.4, 8.93].forEach((ratio, index) => {
      tone(ctx, { from: 1046 * ratio, start: now, attack: 0.003, peak: 0.16 / (index + 1), decay: 0.62 - index * 0.12 });
    });
  },
  B: (ctx, now) => {
    tone(ctx, { type: "triangle", from: 116, to: 98, start: now, attack: 0.05, peak: 0.2, decay: 0.55 });
    tone(ctx, { from: 174, to: 147, start: now, attack: 0.06, peak: 0.07, decay: 0.45 });
    hiss(ctx, { filter: "bandpass", frequency: 900, to: 500, q: 0.8, start: now, attack: 0.08, peak: 0.05, decay: 0.45 });
  },
  G: (ctx, now) => {
    tone(ctx, { from: 260, to: 170, start: now, attack: 0.002, peak: 0.22, decay: 0.11, glide: 0.06 });
    hiss(ctx, { filter: "bandpass", frequency: 1300, q: 4, start: now, attack: 0.001, peak: 0.12, decay: 0.03 });
    [0.06, 0.13, 0.19, 0.27].forEach((offset, index) => {
      hiss(ctx, { filter: "highpass", frequency: 3800 + index * 500, start: now + offset, attack: 0.02, peak: 0.035, decay: 0.09 });
    });
  },
  C: (ctx, now) => {
    tone(ctx, { from: 2093, start: now, attack: 0.002, peak: 0.13, decay: 0.5 });
    tone(ctx, { from: 3140, start: now, attack: 0.002, peak: 0.06, decay: 0.35 });
    tone(ctx, { from: 4198, start: now + 0.004, attack: 0.002, peak: 0.04, decay: 0.25 });
  },
};

/** The sound of checking a color. */
export function playPick(letter: ManaColor): void {
  play(PICKS[letter]);
}

/** Pressing generate: a lever clunk followed by a release of steam. */
export function playLever(): void {
  play((ctx, now) => {
    hiss(ctx, { filter: "highpass", frequency: 1600, q: 2, start: now, attack: 0.001, peak: 0.12, decay: 0.02 });
    tone(ctx, { from: 120, to: 52, start: now + 0.01, attack: 0.004, peak: 0.25, decay: 0.2, glide: 0.12 });
    hiss(ctx, { filter: "lowpass", frequency: 260, start: now + 0.01, attack: 0.003, peak: 0.18, decay: 0.08 });
    hiss(ctx, { filter: "highpass", frequency: 2600, to: 4200, start: now + 0.14, attack: 0.09, peak: 0.09, decay: 0.55 });
  });
}

const SPARKLES = [2637, 3520, 3136, 4186, 2794, 3951];

/** A card reveal: a whoosh and a sparkle; a strong card adds a deep forge boom. */
export function playReveal(tier: "casual" | "medium" | "strong"): void {
  play((ctx, now) => {
    hiss(ctx, { filter: "bandpass", frequency: 380, to: 2600, q: 1.2, start: now, attack: 0.22, peak: 0.16, decay: 0.28 });
    const count = tier === "casual" ? 3 : tier === "medium" ? 4 : 6;
    SPARKLES.slice(0, count).forEach((frequency, index) => {
      tone(ctx, { from: frequency, start: now + 0.26 + index * 0.055, attack: 0.002, peak: 0.07, decay: 0.28 });
    });
    if (tier === "strong") {
      tone(ctx, { from: 72, to: 34, start: now + 0.2, attack: 0.012, peak: 0.25, decay: 0.85, glide: 0.6 });
      hiss(ctx, { filter: "lowpass", frequency: 180, start: now + 0.2, attack: 0.01, peak: 0.16, decay: 0.5 });
    }
  });
}

/** A soft mechanical tick between the steps of a job. */
export function playStepTick(): void {
  play((ctx, now) => {
    hiss(ctx, { filter: "bandpass", frequency: 3200, q: 6, start: now, attack: 0.001, peak: 0.09, decay: 0.018 });
    tone(ctx, { type: "triangle", from: 900, to: 640, start: now, attack: 0.001, peak: 0.06, decay: 0.04 });
  });
}
