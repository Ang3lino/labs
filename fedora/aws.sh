#!/bin/bash

# https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli
brew tap hashicorp/tap
brew install hashicorp/tap/terraform

# https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# https://nodejs.org/en/download
# Download and install nvm:
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
# in lieu of restarting the shell
\. "$HOME/.nvm/nvm.sh"
# Download and install Node.js:
nvm install 24
# Verify the Node.js version:
node -v # Should print "v24.13.1".
# Verify npm version:
npm -v # Should print "11.8.0".

sudo npm install -g aws-cdk

curl -fsSL https://get.pulumi.com | sh

# setup
# --------------------------------------------------------------------------------
aws configure
