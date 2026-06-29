# Git stuff — personal reference

Personal cheat sheet of git/GitHub concepts and habits to keep reinforcing.
Not project documentation — see CLAUDE.md for that.

## The three-stage model

Working directory (your edits) -> staging area (`git add`) -> committed (`git commit`, saved to local history).
`git status` tells you which state your files are in. Most git confusion traces back to not knowing this.

## Core commands, in order

1. `git status` — check state before doing anything.
2. `git pull origin main` — fetch + merge remote changes into your local branch. Do this at the
   start of every session, before branching or editing, to avoid working on stale history.
3. `git add <file>` — stage changes (does NOT touch the branch yet).
4. `git commit -m "message"` — saves a snapshot to your LOCAL repo history. This is "publishing
   locally" — nothing is sent to GitHub yet.
5. `git push origin main` — upload your local commits to GitHub. If rejected ("fetch first"),
   someone (including past-you on another device) pushed commits you don't have — go back to
   step 2, resolve any conflict, then push again.

## Key terms

- **Repo** = a folder + a hidden `.git` subfolder containing the full commit history/database.
  Delete `.git` and it's just a folder again.
- **Branch** = a movable pointer to a line of commits. `main` is just a branch by convention.
- **HEAD** = where you currently are (usually = tip of your current branch).
- **Remote / `origin`** = the conventional nickname for "the GitHub copy of this repo." Local and
  remote are separate until you push/pull/fetch.
- **`origin/main`** = a local, cached bookmark of where GitHub's `main` was last time you checked
  in (push/pull/fetch). Not live — `git status` is reporting the last-known state, not real-time.
- **Credential / token** = a scoped, revocable secret (not your literal GitHub password) used to
  authenticate pushes. Stored by Git Credential Manager in the OS credential vault.

## Switching / creating branches

- `git switch <branch-name>` — switch to an existing branch.
- `git switch -c <new-branch-name>` — create and switch in one step.
- (`git checkout <branch-name>` also works — older/more overloaded command; `switch` was split
  out specifically for changing branches.)

## Merge conflicts — what to do

1. Conflict markers appear in the file: `<<<<<<< HEAD` ... `=======` ... `>>>>>>> <commit>`.
2. Find them: search the file for `<<<<<<<` / `=======` / `>>>>>>>`.
3. Decide what the final content should be (often: keep both additions, not pick one side).
4. Delete the markers, leaving the resolved content.
5. `git add <file>` then `git commit` (no new message needed — finishes the merge).
6. `git push origin main`.

## Cross-device habit (multiple desktops, one repo)

- `git pull origin main` at the **start** of every session, on every device, before branching or
  editing — prevents working on stale history and reduces conflict frequency.
- Treat git history + CLAUDE.md as the source of truth for "where things stand" — local chat/agent
  session history does NOT sync between devices.

## Workflow goal (once doing real feature work)

- Branch per feature/task (`feat/ingest-script`), merge into `main` via PR even solo — gives a
  review checkpoint and a documented "why," not just "what." Delete branch after merge.
- Small, focused commits with messages explaining *why*.
- Never commit secrets (API keys, tokens, DB connection strings) — use `.env`, which is gitignored.
- Don't commit data artifacts (raw pulls, exports, local DB files) — regenerable, not source of truth.

## First real PR/merge loop (lessons from doing it)

- `gh pr create` without `--body` drops you into your default terminal editor
  (here, `nano`) pre-filled with your commit messages, so you can edit the PR
  description before it actually creates the PR. Save (Ctrl+O, Enter) and exit
  (Ctrl+X) to let `gh` pick it up — see Linux/WSL notes for the keys.
- **Creating a PR ≠ merging it.** The PR just opens for review; `main` and the
  feature branch stay separate until you click "Merge" (or run
  `gh pr merge <number>`).
- **Merging ≠ deleting the branch.** Both GitHub and your local clone keep the
  merged branch around afterward. Clean up explicitly:
  ```bash
  git checkout main
  git pull
  git branch -d feat/branch-name              # delete local branch
  git push origin --delete feat/branch-name   # delete remote branch
  ```
  (GitHub's merged-PR page also has a one-click "Delete branch" button as an
  alternative to the `push origin --delete` line.)

## Tier 3 (don't worry about yet)

Rebase, cherry-pick, stash, reflog, bisect, submodules — situational tools, learn them when a real
problem demands it, not by studying cold.
