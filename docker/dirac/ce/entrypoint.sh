#!/bin/bash

set -e

/usr/sbin/automount
exec /usr/sbin/sshd -D
