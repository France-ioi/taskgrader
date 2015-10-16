#!/bin/sh

# This script is a simple generator.
# It tests simple generation and dependencies.
# It will generate three tests, and needs its dependency "gen1-data.dat" to be
# present in its execution directory.

echo 10 > test1-gen1.in
echo 30 > test2-gen1.in
cat gen1-data.dat > testdat-gen1.in
