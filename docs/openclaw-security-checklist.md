# OpenClaw Expansion Plan + Security Checklist

This guide describes how to expand local-LLM agents from chat-only behavior to actionable workflows (file organization, email triage, and similar tasks) using OpenClaw-style computer-use tooling, while protecting the developer machine.

## 1) Security assumptions

- The developer machine contains high-value personal and work data.
- Local LLM outputs are not automatically trustworthy and may be prompt-injected.
- Tool adapters (filesystem, email, browser) are stronger than the model and must enforce policy.
- Any capability that can write files, send messages, or call APIs is high risk.
- Logs and chat transcripts can leak secrets if not redacted.

## 2) Capability model for non-chat actions

Use a capability-gated model instead of globally enabling tools:

1. `chat_only`
   - No side effects.
2. `workspace_read`
   - Read project files only.
3. `workspace_write`
   - Create/update files inside project workspace.
4. `personal_files_limited`
   - User-approved folders only; no recursive destructive operations.
5. `email_read`
   - Read + summarize only.
6. `email_write`
   - Draft only by default; send requires explicit confirmation.
7. `external_actions`
   - Third-party APIs/browser actions with explicit consent.

## 3) OpenClaw integration recommendations

- Run OpenClaw actions through a policy middleware layer (not direct model-to-tool).
- Enforce path allowlists for filesystem operations.
- Enforce domain/account allowlists for network/email operations.
- Require per-session user approval for each capability above `workspace_write`.
- Attach a deterministic action ID and audit record for every side-effecting step.

## 4) Vulnerability checklist

Use this checklist before enabling new capabilities.

### A. Prompt injection and command abuse
- [ ] Tool calls are validated against an allowlist of verbs + arguments.
- [ ] Model output cannot execute shell directly without parser/validator.
- [ ] External content (web/email/docs) is treated as untrusted instructions.
- [ ] Suspicious instructions trigger human confirmation.

### B. Filesystem risk
- [ ] Deny writes outside approved roots by default.
- [ ] Block destructive glob patterns (`*`, recursive delete) unless explicitly confirmed.
- [ ] Enforce max file count/size limits for bulk actions.
- [ ] Keep rollback metadata (backup, move-log, or git diff).

### C. Email/account risk
- [ ] OAuth scopes are least-privilege (`read` before `send`).
- [ ] Sending email requires explicit final confirmation.
- [ ] Sensitive entities (SSNs, API keys, financial data) trigger redaction checks.
- [ ] Account selection is explicit when multiple inboxes exist.

### D. Secrets and credentials
- [ ] Secrets are loaded from secure storage, never hardcoded.
- [ ] Logs redact tokens, cookies, and auth headers.
- [ ] Clipboard/session artifacts are cleared after use.
- [ ] No secrets are written to commits or telemetry.

### E. Supply chain and runtime
- [ ] Tool/plugin sources are pinned and verified.
- [ ] Dependency updates include vulnerability scanning.
- [ ] Sandbox is enforced for code execution tasks.
- [ ] Network egress policy is explicit and minimal.

### F. Observability and incident response
- [ ] Side-effecting operations are logged with timestamp, actor, action, target.
- [ ] User can review and export activity history.
- [ ] “Panic stop” disables all external actions immediately.
- [ ] Recovery playbook exists for accidental file/email actions.

## 5) Safe defaults for “organize files” and “check email”

### Organize files
- Default mode: preview only (proposed moves).
- Require approval before applying move/delete operations.
- Keep an undo map: original path -> new path.

### Check email
- Default mode: summarize unread + suggest replies.
- Draft responses only; send is separate explicit action.
- Never auto-open attachments without malware scanning.

## 6) Developer-machine hardening requirements

- Keep agent runtime in workspace sandbox whenever possible.
- Disable access to browser profiles, SSH keys, and OS keychain by default.
- Require explicit opt-in for any personal directory access.
- Rotate tokens used by agent integrations and use short-lived credentials.
- Add CI guardrails for secret scanning and dangerous command detection.

## 7) Minimum acceptance criteria

Before enabling expanded OpenClaw capabilities in production-like use:

- [ ] Capability gates are implemented and tested.
- [ ] Confirmation UX exists for high-risk actions.
- [ ] Audit logging and redaction are verified.
- [ ] Undo/recovery is validated for file operations.
- [ ] Security checklist above is reviewed per release.
