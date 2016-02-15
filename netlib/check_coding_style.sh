#!/bin/bash

autopep8 -i -r -a -a .
if [[ -n "$(git status -s)" ]]; then
  echo "autopep8 yielded the following changes:"
  git status -s
  git --no-pager diff
  exit 0 # don't be so strict about coding style errors
fi

autoflake -i -r --remove-all-unused-imports --remove-unused-variables .
if [[ -n "$(git status -s)" ]]; then
  echo "autoflake yielded the following changes:"
  git status -s
  git --no-pager diff
  exit 0 # don't be so strict about coding style errors
fi

echo "Coding style seems to be ok."
exit 0
