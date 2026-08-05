#!/bin/bash
REAL=/Library/PostgreSQL/18/bin/pg_config
SDKROOT=$(xcrun --show-sdk-path)

case "$1" in
  --cppflags|--ldflags)
    "$REAL" "$@" | sed 's/-isysroot [^ ]*//g' | sed "s|$| -isysroot $SDKROOT|"
    ;;
  *)
    "$REAL" "$@"
    ;;
esac
