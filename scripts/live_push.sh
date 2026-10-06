#!/usr/bin/env bash
# ব্যবহার: live_push.sh <ফোল্ডার>   ফোল্ডারের *.json ফাইল 'live' ব্রাঞ্চে পাঠায়।
# প্রতিবার ব্রাঞ্চ নতুন করে বানিয়ে force-push হয়, তাই ইতিহাস ফুলে ওঠে না এবং main ব্রাঞ্চের সাথে সংঘাত হয় না।
set -euo pipefail
SRC="$1"
REMOTE="${LIVE_REMOTE:-https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git}"
WORK="$(mktemp -d)"
cp "$SRC"/*.json "$WORK"/
cd "$WORK"
git init -q -b live
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add -A
git commit -q -m "live data $(date -u +%FT%TZ)"
git push -q --force "$REMOTE" live
echo "✅ live ব্রাঞ্চে পাঠানো হয়েছে"
