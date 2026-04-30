# AGENTS.md

Instructions for AI coding agents working in this repo.

## What this is

`owa-mail` is a small stdlib-only Python CLI (package at `owa_mail/`,
~1100 lines split across a handful of modules) for reading, sending,
scheduling and managing Microsoft 365 / Outlook mail from the
terminal. JSON on stdout, logs on stderr, `--pretty` for humans.

The tool is a sibling of [`owa-piggy`](../owa-piggy) and
[`owa-cal`](../owa-cal); the three share layout, coding style and
auth contract. Default auth path: shell out to `owa-piggy` on `$PATH`
(treat them as POSIX utils piped together); owa-piggy owns the
refresh token, owa-mail stores only an optional profile alias
(`owa_piggy_profile`). Alternative path: set `OUTLOOK_APP_CLIENT_ID`
(plus `OUTLOOK_REFRESH_TOKEN` / `OUTLOOK_TENANT_ID` in the config
file) to use a user-owned app registration directly.

## Ground rules

- **Stdlib only** at runtime. No `requests`, no `msal`, no deps.
  `pytest` is dev-only under `[project.optional-dependencies] test`.
- **JSON on stdout, logs on stderr.** Callers pipe `owa-mail messages`
  into `jq`. Do not print progress, timing, or decorations to stdout.
- **Never commit real refresh tokens, access tokens, tenant IDs, or
  `~/.config/owa-mail/config` contents**, even in tests or fixtures.
  Use obvious fakes (`"fake-rt-for-tests"`). Refresh-token handling
  applies only on the app-registration path; on the owa-piggy path
  owa-mail holds no secrets.
- **Do not switch the backend to Microsoft Graph on the owa-piggy
  auth path** unless you've verified the SPA client carries the mail
  scopes you need on the Graph audience. The Outlook REST v2 audience
  is what `owa-cal` uses and what OWA itself uses for mail; staying
  there keeps the three tools symmetric. Graph is an option only for
  users with their own `OUTLOOK_APP_CLIENT_ID`.
- **Preserve the scheduled-send invariant.** `--send-at` works by
  attaching the `PR_DEFERRED_SEND_TIME` extended property
  (`PropertyId = "SystemTime 0x3FEF"`) to a draft, then calling
  `/send`. Don't change the property tag or the dispatch order
  (create-draft, then send) without checking that Exchange Transport
  still defers the send.
- **Outlook REST `$search` and `$filter` are mutually exclusive.** The
  `messages` command rejects `--search` combined with the filter
  flags (`--unread`, `--from`, `--subject`, `--since`, `--until`).
  Don't silently drop one to "fix" a future bug report; that's how
  the user ends up confused about which results were actually
  returned.

## Layout

```
owa_mail/
  __init__.py        # re-exports `main` so `owa-mail = "owa_mail:main"` resolves
  __main__.py        # `python -m owa_mail`
  cli.py             # arg parsing + dispatch + cmd_* handlers
  config.py          # CONFIG_PATH, load_config, save_config, config_set
  dates.py           # today/tomorrow/yesterday, resolve_date
  messages.py        # normalize_message, build_message_body,
                     # build_send_payload, build_draft_payload,
                     # build_reply_patch, build_mark_patch
  folders.py         # WELL_KNOWN map, resolve_folder_id, folder_messages_path,
                     # normalize_folder
  scheduled.py       # build_deferred_send_props (PR_DEFERRED_SEND_TIME)
  format.py          # --pretty formatters (messages, message, folders)
  auth.py            # do_token_refresh (app-reg path + owa-piggy bridge)
  api.py             # Outlook REST HTTP helper (urllib)
  jwt.py             # token_minutes_remaining (no signature validation)
scripts/
  add-to-path.sh     # pipx-based installer shim
tests/               # pytest suite around pure functions + CLI smoke
pyproject.toml
README.md
SECURITY.md
```

## Working on this repo

- **Read before editing.** Don't change code you haven't read.
- **Preserve behavior** unless a commit explicitly changes it. Recent
  commits encode subtle decisions: env-wins-over-config precedence,
  atomic config writes with 0600 perms, unknown-command check before
  auth, `--search` xor filter flags, mark mutually-exclusive flag
  pairs. Do not regress those.
- **Don't add abstractions.** A `class MailClient` wrapping three
  `urlopen` calls is noise. Flat functions are the norm.
- **Test what matters.** Pure functions (`resolve_folder_id`,
  `normalize_message`, `build_message_body`, `build_draft_payload`,
  `build_reply_patch`, `build_mark_patch`, `to_outlook_utc`,
  `parse_kv_stream`, `format_messages_pretty`) plus CLI dispatch are
  the test targets. Network calls and interactive prompts are not.

## Verification before claiming done

- `python -m compileall -q owa_mail` passes.
- `python -m owa_mail --help` runs without traceback on a machine
  with no config.
- `pytest -q` is green.
- If you touched the read/write path: `owa-mail messages --pretty`
  and `owa-mail send --to <self> --subject test --body hi` still
  work against a real configured profile. If you cannot run against
  a real profile, say so explicitly rather than claiming it works.

## Commits and PRs

- Short imperative commit messages. One line is usually enough;
  expand in the body only when the *why* isn't obvious from the
  diff.
- One logical change per commit.
- Do not push or open PRs without the user asking. Do not force-push
  `main`.

## Cutting a release (only when the user asks)

Same flow as `owa-cal`. Releases ship through the Homebrew tap at
`~/Code/homebrew-tap` (`damsleth/homebrew-tap` on GitHub). The
formula pins a specific tag tarball and sha256, so a version bump
here must be followed by a tap update or `brew upgrade` stays on
the old version.

When the user says "cut a release":

1. Pick the bump. Patch (`0.1.0 -> 0.1.1`) for fixes; minor for
   new flags / behaviors. Never bump major without explicit ask.
2. Commit the feature work separately from the version bump.
3. Update `pyproject.toml` `version`. No other file tracks it.
4. Push `main`, then `git tag vX.Y.Z && git push origin vX.Y.Z`.
5. Fetch the GitHub-generated tarball and compute its sha256,
   update the Homebrew tap formula, push, then `brew upgrade`.

If any step fails midway (tag push rejected, sha mismatch, tap push
rejected), stop and surface the error - do not try to "fix" a
published tag by force-pushing.

## What NOT to do

- Don't register an Azure AD app "just to make auth simpler" - that
  is what `owa-piggy` exists to avoid. The app-registration path is
  optional for users who already have one.
- Don't add telemetry, crash reporting, update checks, or any
  network call beyond the Outlook REST API and
  `login.microsoftonline.com`.
- Don't add HTML-to-text rendering with a third-party HTML parser to
  "improve" `--pretty` output. Stdlib-only is the point.
- Don't add emoji, badges, or marketing copy to docs.
- Don't break the `jq`-friendly JSON output contract on stdout.
