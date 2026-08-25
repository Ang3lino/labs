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

## GitHub CLI / Copilot auth

Token is stored in the **system keyring** (not in `auth.db` — that file is empty).

```bash
# Show token on source machine
gh auth token

# Transfer to another machine via pipe
gh auth token > /tmp/gh-token.txt
scp /tmp/gh-token.txt user@host:/tmp/
rm /tmp/gh-token.txt

# On target: login with token
cat /tmp/gh-token.txt | gh auth login --with-token
rm /tmp/gh-token.txt

# Or just authenticate directly on the target (easiest)
gh auth login
```

If `gh` not installed: `sudo apt install -y gh`

## Troubleshooting

**HTTP server: curl hangs on receiver**
- macOS firewall blocks incoming. Either disable firewall temporarily or use SCP instead.

**SCP: connection refused**
- SSH server not installed on receiver. Fix: `sudo apt install -y openssh-server`

## OpenCode credentials

OpenCode uses its own API key, separate from GitHub Copilot's `auth.db`.

```bash
# On the target machine, add to ~/.secrets (sourced by .zshrc automatically)
echo 'export OPENCODE_API_KEY=your-key-here' >> ~/.secrets
```

To use a specific provider config:

```bash
# Pick one of the single-provider configs
cp ~/.config/opencode/oh-my-openagent.github-copilot.json ~/.config/opencode/oh-my-openagent.json
cp ~/.config/opencode/oh-my-openagent.bedrock.json ~/.config/opencode/oh-my-openagent.json
cp ~/.config/opencode/oh-my-openagent.opencode-go.json ~/.config/opencode/oh-my-openagent.json
```
