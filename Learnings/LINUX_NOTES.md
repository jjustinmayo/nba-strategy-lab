# Linux / WSL Notes — personal reference

Personal cheat sheet on Linux/WSL concepts hit while setting up this project.
Not project documentation — see CLAUDE.md for that.

## What WSL actually is

WSL (Windows Subsystem for Linux) is a **real, separate Linux environment**
running alongside Windows — not a theme on top of PowerShell. It has its own
filesystem, its own Python, its own package manager. The bottom-left "WSL"
badge in VS Code means the editor is connected to that Linux machine (via the
Remote-WSL extension), not running locally on Windows.

## Two filesystems, two worlds

- **WSL-native**: `/home/<user>/...` — what Windows sees as `\\wsl$\Ubuntu\home\<user>\...`.
- **Windows-native**: `C:\...` — what WSL sees as `/mnt/c/...`.

Crossing the boundary (e.g. a Linux process reading `/mnt/c/...`) is slow,
because every file op gets translated between the two OS's file APIs. Keep
project files on the Linux side (`~/...`) for anything you'll be running
`python`/`pip`/`git` against frequently.

**Why this project moved here:** Windows **Smart App Control** blocked
pandas' compiled binaries on the native-Windows setup; WSL sidesteps that
entirely and also mirrors the Linux servers/containers most real DE/AI
pipelines actually run on.

## venv activation differs by OS

- Linux/WSL: `source .venv/bin/activate`
- Windows PowerShell: `.venv\Scripts\Activate.ps1`

Same concept (put this project's isolated Python + packages first on PATH),
different shell syntax.

## `nano` basics (hit this live via `gh pr create`)

`gh pr create` (and `git commit` without `-m`) drops you into your shell's
default text editor to write a message — on this setup, that's `nano`.

- **Ctrl+O** — "write out" (save). It'll prompt for a filename; press **Enter**
  to confirm the existing one.
- **Ctrl+X** — exit. (Do this *after* saving, or it'll ask if you want to save
  on the way out.)
- The `^` shown in nano's bottom menu means **Ctrl**, not Shift — e.g. `^G` =
  Ctrl+G for help.

## Tier 3 (don't worry about yet)

Shell scripting (`bash` functions, `.bashrc`), permissions (`chmod`/`chown`),
process management (`ps`, `kill`) — situational, learn on demand.
