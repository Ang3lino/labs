#!/bin/bash
brew install neovim
sudo apt install vim tmux

# "required"
mv ~/.config/nvim{,.bak}

# LazyVim - https://www.lazyvim.org/installation
git clone https://github.com/LazyVim/starter ~/.config/nvim
rm -rf ~/.config/nvim/.git

nvim
