#!/usr/bin/env bash

for f in *.in
do
  pip-compile --generate-hashes $f
done

# remove editable dependencies.
sed -i -E 's/^(-e .+)/# \1/g' *.txt
