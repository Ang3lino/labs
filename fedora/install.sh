#!/bin/bash
sudo dnf install vim neovim tmux -y
sudo dnf htop btop fastfetch -y

# https://youtu.be/GoCPO_If7kY?si=-UF6Ho6mqyOgvpwf
sudo dnf install gnome-tweaks -y
sudo dnf install gnome-shell-extension-dash-to-dock -y
# https://rpmfusion.org/Configuration

# https://www.lazyvim.org/installation
# ---------------------------------------------------------------------------------
# required
mv ~/.config/nvim{,.bak}

# optional but recommended
mv ~/.local/share/nvim{,.bak}
mv ~/.local/state/nvim{,.bak}
mv ~/.cache/nvim{,.bak}

git clone https://github.com/LazyVim/starter ~/.config/nvim

rm -rf ~/.config/nvim/.git

# https://opencode.ai/
# ---------------------------------------------------------------------------------
curl -fsSL https://opencode.ai/install | bash

# https://docs.rancherdesktop.io/getting-started/installation/
# ---------------------------------------------------------------------------------
sudo dnf config-manager addrepo --from-repofile=https://download.opensuse.org/repositories/isv:/Rancher:/stable/fedora/isv:Rancher:stable.repo
sudo dnf install rancher-desktop -y

# homebrew
# ---------------------------------------------------------------------------------
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
# in order to add to the path
echo >>/home/angel/.bashrc
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv bash)"' >>/home/angel/.bashrc
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv bash)"
# recommended
sudo dnf group install development-tools
sudo dnf install gcc
# K8s
brew install kubectl k9s

# VLC - ttps://www.videolan.org/vlc/download-fedora.htmlhttps://www.videolan.org/vlc/download-fedora.html
# ---------------------------------------------------------------------------------
su -
dnf install https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
dnf install https://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
dnf install vlc
dnf install python-vlc # (optional)

# Xelatex
# ---------------------------------------------------------------------------------
sudo dnf install -y texlive-scheme-full
# latexmk -xelatex -pvc cv.tex # run in watch mode
