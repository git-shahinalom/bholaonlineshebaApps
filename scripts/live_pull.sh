#!/usr/bin/env bash
# live ব্রাঞ্চের বর্তমান ফাইলগুলো live/ ফোল্ডারে আনে (না থাকলে চুপচাপ এগিয়ে যায়)
set -u
mkdir -p live
if git fetch -q origin live 2>/dev/null; then
  for f in weather.json alerts.json; do
    git show "FETCH_HEAD:$f" > "live/$f" 2>/dev/null || rm -f "live/$f"
  done
fi
ls -la live
