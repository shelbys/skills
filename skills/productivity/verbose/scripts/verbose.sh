#!/bin/sh

echo "Switching to verbose..."
[ -f ~/.claude/.caveman-active ] && rm ~/.claude/.caveman-active
[ -f ~/.claude/.terse-active ] && rm ~/.claude/.terse-active
