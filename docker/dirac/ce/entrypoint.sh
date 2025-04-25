#!/bin/bash

set -e

exec /usr/sbin/sshd -D -e -o LogLevel=DEBUG3
