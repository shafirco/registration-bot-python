#!/bin/bash

# ----------------------
# KUDU Deployment Script for Python
# ----------------------

# Prerequisites
# -------------

# Verify python installed
command -v python3 >/dev/null 2>&1 || { echo >&2 "Python 3 is required but not installed."; exit 1; }

# Setup
# -----

ARTIFACTS=$PWD/../artifacts

if [[ ! -n "$DEPLOYMENT_SOURCE" ]]; then
  DEPLOYMENT_SOURCE=$PWD
fi

if [[ ! -n "$DEPLOYMENT_TARGET" ]]; then
  DEPLOYMENT_TARGET=$ARTIFACTS/wwwroot
else
  KUDU_SERVICE=true
fi

if [[ ! -n "$NEXT_MANIFEST_PATH" ]]; then
  NEXT_MANIFEST_PATH=$ARTIFACTS/manifest

  if [[ ! -n "$PREVIOUS_MANIFEST_PATH" ]]; then
    PREVIOUS_MANIFEST_PATH=$ARTIFACTS/manifest
  fi
fi

if [[ ! -n "$KUDU_SYNC_CMD" ]]; then
  # Install kudu sync
  echo Installing Kudu Sync
  npm install kudusync -g --silent
  exitWithMessageOnError "kudu sync installation failed"

  if [[ `npm config get prefix` != "" ]]; then
    KUDU_SYNC_CMD=`npm config get prefix`/bin/kuduSync
  else
    KUDU_SYNC_CMD=kuduSync
  fi
fi

##################################################################################################################################
# Deployment
# ----------

echo Python Deployment

# 1. KuduSync
if [[ "$IN_PLACE_DEPLOYMENT" -ne "1" ]]; then
  "$KUDU_SYNC_CMD" -v 50 -f "$DEPLOYMENT_SOURCE" -t "$DEPLOYMENT_TARGET" -n "$NEXT_MANIFEST_PATH" -p "$PREVIOUS_MANIFEST_PATH" -i ".git;.hg;.deployment;deploy.sh"
  exitWithMessageOnError "Kudu Sync failed"
fi

# 2. Create virtual environment
if [ ! -d "$DEPLOYMENT_TARGET/antenv" ]; then
  echo "Creating virtual environment"
  python3 -m venv "$DEPLOYMENT_TARGET/antenv"
  exitWithMessageOnError "Failed to create virtual environment"
fi

# 3. Activate virtual environment
echo "Activating virtual environment"
source "$DEPLOYMENT_TARGET/antenv/bin/activate"
exitWithMessageOnError "Failed to activate virtual environment"

# 4. Install packages
echo "Installing packages"
python -m pip install --upgrade pip
if [ -f "$DEPLOYMENT_TARGET/requirements.txt" ]; then
  pip install -r "$DEPLOYMENT_TARGET/requirements.txt"
  exitWithMessageOnError "pip failed"
fi

# 5. Copy web.config
if [[ -f "$DEPLOYMENT_SOURCE/web.config" ]]; then
  cp "$DEPLOYMENT_SOURCE/web.config" "$DEPLOYMENT_TARGET/web.config"
fi

##################################################################################################################################

exitWithMessageOnError () {
  if [ ! $? -eq 0 ]; then
    echo "An error has occurred during web site deployment."
    echo $1
    exit 1
  fi
}

echo "Finished successfully."
