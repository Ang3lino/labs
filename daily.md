

8-31
Yesterday:
- tmux installation on Windows

Findings:
- MSYS2 pacman fails with SSL errors due to Zscaler corporate proxy intercepting HTTPS
  - Root cause: MSYS2's OpenSSL doesn't trust Zscaler's root CA
  - Fix: export Zscaler cert from Windows cert store, append to /usr/ssl/certs/ca-bundle.crt
  - Even after SSL fix, Zscaler blocks .zst file downloads (403 filetype policy)
- Git Bash lacks pacman by default (minimal MSYS2); bootstrap script no longer exists
- Cygwin doesn't include tmux by default; needs `setup-x86_64.exe -q -P tmux`
- Solution: `winget install arndawg.tmux-windows` — native Windows build, no MSYS2 needed
  - Installs tmux 3.6a-win32 via GitHub releases (Zscaler allows GitHub)
  - Adds to PATH automatically

Today:
- OS shutdown for updates

---

8-5
Yesterday:
- Chaos Engineering Sync meeting
- MDC Connect
- Devtalk git antipatterns
- Review of EC2 instance type for ML apps

Today:
- Optimization of ML apps with GPU

---

Yesterday:
- Bench start survey
- Normalization of sound for transfer learning

Today: 
- Machine Translation Review with PyTorch
- BLEU metric for evaluation

---

Yesterday:
- Hands On face detection
- Hands on voice dialization

Today:
- Hands on safeguards comparisons
- MDC Connect
