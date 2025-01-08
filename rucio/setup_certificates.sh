#!/bin/bash

set -eux -o pipefail

# voms-proxy-init requires certs only readable by the current user
# so copy the user certs, chown them to root to create the proxy owned by root
# copy user certs with fixed permissions to volumes used by other rucio services
mkdir -p /root/certs
cp /home/user/.globus/user{cert,key}.pem /root/certs/
ls -l /root/certs/
voms-proxy-init -valid 9999:00 -cert /root/certs/usercert.pem -key /root/certs/userkey.pem -out /root/certs/x509up
