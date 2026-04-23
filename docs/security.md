# Security notes (local CLI)

- Do not commit `.env` or API keys; add `.env` to `.gitignore` and rotate keys if exposed.
- Restrict permissions on `~/.ai-team` (or `%USERPROFILE%\.ai-team` on Windows): config and logs may contain sensitive metadata.
- `EDITOR` is validated before launching an external editor; avoid bypassing the helper with raw `subprocess` + shell.
- Monitor command queue entries are allowlisted and `project_root` / `prompt` are validated before drain executes actions.
