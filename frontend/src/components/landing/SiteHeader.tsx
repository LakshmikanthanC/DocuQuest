"use client";

import { useState } from "react";
import Link from "next/link";
import ThemeToggle from "@/components/theme/ThemeToggle";
import Icon from "@/components/ui/Icon";
import Logo from "@/components/ui/Logo";
import { cx } from "@/lib/cx";
import { NAV_LINKS } from "./content";

export default function SiteHeader() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-line/80 glass">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center gap-6 px-5 sm:px-6">
        <Link href="/" aria-label="RAG Assistant home" className="shrink-0">
          <Logo />
        </Link>

        <nav aria-label="Main" className="hidden flex-1 items-center gap-1 md:flex">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="rounded-lg px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2 md:ml-0">
          <ThemeToggle className="hidden sm:inline-flex" />
          <Link href="/workspace" className="btn-primary btn-sm hidden sm:inline-flex">
            Open workspace
            <Icon name="arrowRight" className="size-3.5" />
          </Link>
          <button
            type="button"
            onClick={() => setMenuOpen((open) => !open)}
            className="icon-btn md:hidden"
            aria-expanded={menuOpen}
            aria-controls="mobile-nav"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
          >
            <Icon name={menuOpen ? "close" : "menu"} className="size-5" />
          </button>
        </div>
      </div>

      <div
        id="mobile-nav"
        className={cx(
          "grid border-t border-line transition-[grid-template-rows] duration-300 md:hidden",
          menuOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]",
        )}
      >
        <div className="overflow-hidden">
          <nav
            aria-label="Mobile"
            className="flex flex-col gap-1 px-5 py-4 sm:px-6"
          >
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setMenuOpen(false)}
                className="rounded-lg px-3 py-2.5 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                {link.label}
              </a>
            ))}
            <div className="mt-2 flex items-center gap-3 border-t border-line pt-4">
              <ThemeToggle />
              <Link
                href="/workspace"
                onClick={() => setMenuOpen(false)}
                className="btn-primary btn-sm flex-1"
              >
                Open workspace
                <Icon name="arrowRight" className="size-3.5" />
              </Link>
            </div>
          </nav>
        </div>
      </div>
    </header>
  );
}
