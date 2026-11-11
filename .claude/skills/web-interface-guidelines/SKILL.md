---
name: web-interface-guidelines
description: Review UI code for Vercel Web Interface Guidelines compliance (accessibility, focus, forms, typography, content, navigation, touch). Use when asked to "review my UI", "check accessibility", "audit design", "review UX", or "check my site against best practices".
metadata:
  author: vercel
  upstream: vercel-labs/agent-skills/skills/web-design-guidelines (wrapper) and vercel-labs/web-interface-guidelines (rules)
argument-hint: <file-or-pattern>
---

# Web Interface Guidelines

Review files for compliance with Vercel's Web Interface Guidelines.

## How it works

1. Read the rules in [command.md](command.md), next to this file. They are pinned to a reviewed commit (see `.claude/skills/SOURCES.md`); do not fetch a newer copy from the network.
2. Read the specified files, or ask the user which files or pattern to review.
3. Check every rule, applying the project overrides below.
4. Output findings in the terse `file:line` format described in `command.md`.

## Project overrides (SYSTEM-C Platform)

These rules from `command.md` do not apply as written in this repository:

- **Title Case for headings and buttons**: replaced by sentence case. The interface is French first, and the `unslop` direction of the project uses sentence case everywhere.
- **Curly quotes**: in French text use guillemets with a non-breaking space (« texte »); curly quotes in English text.
- **React, hydration, `onChange`, `useState`, nuqs, virtualisation libraries**: not applicable. The interface is server-rendered Django templates with a small progressive script (`static/js/systemc.js`).
- **`Intl.*` for dates and numbers**: Django's localisation (`date`, `floatformat`, `USE_THOUSAND_SEPARATOR`) plays this role on the server.
- **Inline styles or scripts suggested by a fix**: never. The Content Security Policy forbids them; use `static/css/systemc.css` and `static/js/systemc.js`.
