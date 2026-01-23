#!/bin/bash
# I'm using Kubuntu, however for mac it's pretty similar, and for windows you just set WSL in Rancher GUI

# https://docs.rancherdesktop.io/getting-started/installation/
curl -s https://download.opensuse.org/repositories/isv:/Rancher:/stable/deb/Release.key | gpg --dearmor | sudo dd status=none of=/usr/share/keyrings/isv-rancher-stable-archive-keyring.gpg
echo 'deb [signed-by=/usr/share/keyrings/isv-rancher-stable-archive-keyring.gpg] https://download.opensuse.org/repositories/isv:/Rancher:/stable/deb/ ./' | sudo dd status=none of=/etc/apt/sources.list.d/isv-rancher-stable.list
sudo apt update
sudo apt install rancher-desktop


# https://brew.sh/
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
# ==> Next steps:
# - Run these commands in your terminal to add Homebrew to your PATH:
echo >> /home/arcangel/.bashrc
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv bash)"' >> /home/arcangel/.bashrc
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv bash)"
# - Install Homebrew's dependencies if you have sudo access:
sudo apt-get install build-essential
#   For more information, see:
#     https://docs.brew.sh/Homebrew-on-Linux
# - We recommend that you install GCC:
brew install gcc
# - Run brew help to get started
# - Further documentation:
#     https://docs.brew.sh
brew install kubectl k9s

# extras
sudo apt install vim tmux
