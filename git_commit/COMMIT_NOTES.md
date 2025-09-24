# Commit Notes and Push Instructions

- Branch: `smartbuild_monitor_automation`
- Remote: `https://github.com/GopiSunware/SmartBuild.git`
- Purpose: Archive tests/verify scripts; consolidate root markdown under `.md/`.

Summary of included changes
- Move root-level `*.md` into `.md/` grouped folders (status-index, testing, analyses, fixes, features, archive)
- Add root `CLAUDE.md` pointer that redirects to `.md/CLAUDE.md`
- Archive `tests/`, root `test_*.py`, and `verify_*` scripts under `archive/cleanup_*`
- Remove repo-level caches (`__pycache__`, `.pytest_cache`) and archive Windows ADS temp files
- Add `scripts/push_smartbuild.sh` to push with a PAT without storing it

Push this branch (PAT route)
```bash
# Preferred: set token only in your shell session
export GH_PAT=ghp_yourFineGrainedTokenGoesHere
# One-time push
git push -u https://x-access-token:${GH_PAT}@github.com/GopiSunware/SmartBuild.git smartbuild_monitor_automation
# Or use helper script
./scripts/push_smartbuild.sh
```

One-step commit and push
```bash
./git_commit/commit_and_push.sh "your commit message"
```

Token guidance
- Do NOT commit tokens/passwords to the repository.
- For convenience, you may store a local (gitignored) file: `.md/git_doc/PRIVATE_GITHUB_PAT.txt` and export from it:
  ```bash
  export GH_PAT=$(cat .md/git_doc/PRIVATE_GITHUB_PAT.txt)
  ```
- To make pushes easier on Windows/macOS, you can use the system credential manager instead of storing plaintext.

Creating a fine‑grained PAT
- GitHub → Settings → Developer settings → Fine‑grained tokens → Generate new token
- Resource owner: `GopiSunware`; Repository: `SmartBuild`
- Permissions → Repository: `Contents: Read and write`, `Metadata: Read`

Rollback instructions
- Undo branch locally: `git checkout main && git branch -D smartbuild_monitor_automation`
- Revert after push: `git revert <commit-sha>`
