# Git Docs and Security

This folder holds developer documentation related to git usage for this repo.

Security policy
- Do NOT commit secrets (PATs, passwords, private keys). Use local gitignored files or your credential manager.
- For PAT-based pushes, export `GH_PAT` in your shell or use a local file `.md/git_doc/PRIVATE_GITHUB_PAT.txt` (gitignored) and `export GH_PAT=$(cat .md/git_doc/PRIVATE_GITHUB_PAT.txt)`.
- For SSH, prefer deploy keys or your user SSH key; keep private keys out of version control.

Files
- `COMMIT_NOTES.md`: how to push the current branch and token guidance.

