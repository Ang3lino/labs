#!/bin/bash

# https://opencode.ai/
#
brew install anomalyco/tap/opencode


# for windows ------------------------------------------------------------------
# install node and docker 1st

# npm: https://nodejs.org/en/download
# Docker has specific installation instructions for each operating system.
# Please refer to the official documentation at https://docker.com/get-started/

# Pull the Node.js Docker image:
docker pull node:24-alpine

# Create a Node.js container and start a Shell session:
docker run -it --rm --entrypoint sh node:24-alpine

# Verify the Node.js version:
node -v # Should print "v24.13.0".

# Verify npm version:
npm -v # Should print "11.6.2".

npm i -g opencode-ai
