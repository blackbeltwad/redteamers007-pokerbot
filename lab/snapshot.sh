#!/bin/sh
# Snapshot the current bot: lab/snapshot.sh v1
set -e
cd "$(dirname "$0")/.."
rm -rf "lab/snapshots/$1" && mkdir -p lab/snapshots && cp -r my_bots/redteamers007 "lab/snapshots/$1"
find "lab/snapshots/$1" -name __pycache__ -prune -exec rm -rf {} +
echo "snapshot lab/snapshots/$1"
