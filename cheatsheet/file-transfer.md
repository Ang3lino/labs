# File Transfer (LAN)

## Quick HTTP server (any OS with Python)

```bash
# Serve current directory
python3 -m http.server 8888 --bind 0.0.0.0    # macOS / Linux
python -m http.server 8888 --bind 0.0.0.0      # Windows
```

```bash
# Grab from another machine
curl http://<ip>:8888/<file> -o <dest>          # macOS / Linux
curl.exe http://<ip>:8888/<file> -o <dest>      # Windows PowerShell (curl = Invoke-WebRequest alias)
```

## SCP

```bash
scp <file> user@host:<dest>                     # macOS / Linux (built-in)
scp <file> user@host:<dest>                     # Windows: Git Bash or enable OpenSSH Client
```

Windows OpenSSH: `Settings > Apps > Optional Features > OpenSSH Client`

## GitHub Copilot credentials

| OS | Path |
|----|------|
| macOS / Linux | `~/.config/github-copilot/auth.db` |
| Windows | `%LOCALAPPDATA%\github-copilot\auth.db` |

```bash
# Share on LAN (run on source, kill after transfer)
cd ~/.config/github-copilot && python3 -m http.server 8888 --bind 0.0.0.0

# Receive
mkdir -p ~/.config/github-copilot
curl http://<ip>:8888/auth.db -o ~/.config/github-copilot/auth.db
```

```powershell
# Receive (Windows PowerShell)
New-Item -ItemType Directory -Force "$env:LOCALAPPDATA\github-copilot"
curl.exe http://<ip>:8888/auth.db -o "$env:LOCALAPPDATA\github-copilot\auth.db"
```

Prefer `scp` over HTTP — no open port window.
