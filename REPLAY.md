# Replay a failed ALPS install and decide what the guide got wrong

You are running inside GitHub Actions. A user ran `alps-install-agent.md` on their machine
and it was logged. Your job is to attempt the same install in an environment resembling
theirs, find out which steps actually work, and propose changes to the guide — but only
where you have evidence.

## Inputs

| What | Where |
|---|---|
| The user's log | `$ORIGINAL_LOG` |
| Parsed fingerprint | `fingerprint.json` |
| The guide under test | `alps-install-agent.md` |
| Whether the environment matches exactly | `$EXACT` (`true` / `false`) |

## How to run commands

**Every install command must go through `$ALPS_EXEC`.** On Linux that puts it inside the
container matching the user's distro, as a non-root user with no sudo. Running it on the
runner directly tests nothing.

```bash
$ALPS_EXEC 'gcc --version'
$ALPS_EXEC 'cd /home/tester && cmake -S alps-src -B build'
```

Use plain Bash (not `$ALPS_EXEC`) only for reading repo files and writing your report.

## What to do

1. **Read the log first.** Find where it failed: the failing commands are already extracted
   into `fingerprint.json` under `failures`. Note the exit code and the error text.

2. **Confirm the environment is close enough.** Run the Step 1 probe through `$ALPS_EXEC` and
   compare it to the `probe_text` in `fingerprint.json`. Record every difference. If
   `$EXACT` is `false` the container is only an approximation of the user's distro, and if
   the fingerprint is macOS the compiler and Python versions will differ from theirs no
   matter what — the runner image is fixed. Say so plainly in your report.

3. **Replay the guide from Step 2**, taking the same route the user took, and answering
   **no** to root. Stop when you reach the failure, or when you have run past the point
   where they failed.

4. **If it failed the same way**, that is a guide bug. Try to fix it. Change one thing at a
   time and record what you tried, including what did not work.

5. **If it did not fail**, the cause is something about their machine that the container
   does not have. That is still a finding: say what differs, and whether the guide could
   detect it in Step 1.

## What to write

Write `findings.md`. This becomes the PR body, so it has to stand on its own:

```markdown
## Environment
target: <image or runner>   exact match: <yes/no>
differences from the user's probe: <list, or "none material">

## What the user hit
step <n>, command `<cmd>`, exit <code>
<the error, verbatim>

## Reproduced
<yes / no — and if no, the most likely reason>

## What I tried
| attempt | result |
|---|---|
| ... | ... |

## Proposed change
<the diff, or "none — see below">

## Confidence
<what would make this more certain: more logs, a real machine, a specific test>
```

## Rules

- **Proposing no change is a valid outcome and often the right one.** One log from one
  machine is one data point. If you cannot reproduce the failure, say so and propose
  nothing. Do not invent a plausible-sounding fix to have something to submit.
- **Only edit the section your evidence covers.** A Rocky 8 log says nothing about Step 5.
- **Do not restructure the document.** Keep the diff under ~40 changed lines. Rewrites are
  not reviewable and destroy hard-won detail.
- **Prefer adding a Pitfalls row over rewriting a step** when the failure is
  environment-specific rather than an error in the instructions.
- **Never add `sudo`.** The no-root path is the whole point of the guide.
- **Record failed attempts.** What did not work is as useful to the next run as what did.
- If a build exceeds the job timeout, stop and report progress. A partial replay with an
  honest note beats a fabricated conclusion.
