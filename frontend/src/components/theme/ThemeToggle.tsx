"use client";

import { useEffect, useLayoutEffect } from "react";
import Icon, { type IconName } from "@/components/ui/Icon";

export type ThemePref = "light" | "dark" | "system";

const STORAGE_KEY = "rag.theme";

const OPTIONS: { value: ThemePref; label: string; icon: IconName }[] = [
  { value: "light", label: "Light", icon: "sun" },
  { value: "dark", label: "Dark", icon: "moon" },
  { value: "system", label: "System", icon: "monitor" },
];

function readPref(): ThemePref {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored === "light" || stored === "dark" || stored === "system"
      ? stored
      : "system";
  } catch {
    return "system";
  }
}

function applyPref(pref: ThemePref): void {
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const dark = pref === "dark" || (pref === "system" && prefersDark);
  const root = document.documentElement;
  root.setAttribute("data-theme", dark ? "dark" : "light");
  root.setAttribute("data-theme-pref", pref);
}

export function setTheme(pref: ThemePref): void {
  applyPref(pref);
  try {
    window.localStorage.setItem(STORAGE_KEY, pref);
  } catch {
    // Storage can be unavailable in private mode; the attribute still applies.
  }
}

/**
 * Keeps the theme attributes authoritative on the client.
 *
 * Renders nothing. The inline script in the root layout applies the stored
 * preference before first paint; this only re-applies it after React's dev-only
 * Strict Mode remount resets <html>, and keeps "system" in step with the OS.
 */
export function ThemeController() {
  useLayoutEffect(() => {
    applyPref(readPref());
  }, []);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      if (readPref() === "system") applyPref("system");
    };
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  return null;
}

/**
 * Light / dark / system segmented control.
 *
 * The active option is styled from the `data-theme-pref` attribute on <html>,
 * so nothing here depends on client-only state and hydration always agrees with
 * the DOM the inline script produced.
 */
export default function ThemeToggle({ className }: { className?: string }) {
  return (
    <div
      role="group"
      aria-label="Colour theme"
      className={
        "inline-flex items-center gap-0.5 rounded-xl border border-line bg-muted/70 p-0.5 " +
        (className ?? "")
      }
    >
      {OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => setTheme(option.value)}
          data-theme-option={option.value}
          title={`${option.label} theme`}
          className="theme-option"
        >
          <Icon name={option.icon} className="size-4" />
          <span className="sr-only">{option.label} theme</span>
        </button>
      ))}
    </div>
  );
}
