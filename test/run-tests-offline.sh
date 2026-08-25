#!/usr/bin/env bash

sudo unshare --net -- sh -c "ip link set lo up; $(which pytest)"
