#!/bin/bash

set -eux -o pipefail

# copy user certs to fix permissions
voms-proxy-init -valid 9999:00 -cert /home/user/.globus/usercert.pem -key /home/user/.globus/userkey.pem


# add the storage element (xrd)
for N in 1 2 3; do
  RSE="STORAGE-${N}"
  rucio rse add --rse-name "STORAGE-${N}"
  rucio rse protocol add \
      --rse-name "${RSE}" \
      --host "rucio-storage-$N" \
      --scheme root \
      --prefix //rucio \
      --port 1094 \
      --impl rucio.rse.protocols.gfal.Default \
      --domain-json '{"wan": {"read": 1, "write": 1, "delete": 1, "third_party_copy_read": 1, "third_party_copy_write": 1}, "lan": {"read": 1, "write": 1, "delete": 1}}' \

  rucio rse attribute add --rse "${RSE}" --key fts --value https://fts:8446

  # this is for some reason I really don't understand needed by the DIRAC-Rucio integration
  rucio rse attribute add --rse "${RSE}" --key ANY --value true
  rucio account limit add --account root --rse-exp "${RSE}" --bytes "infinity"
done


# All RSEs connected to all other RSEs directly for now
for A in 1 2 3; do
  for B in 1 2 3; do
    [ $A == $B ] && continue
    rucio rse distance add --source "STORAGE-$A" --destination "STORAGE-$B" --distance 1 
  done
done

# add a scope
rucio scope add --account root --scope test
fts-rest-whoami -s https://fts:8446
fts-rest-delegate -vf -s https://fts:8446 -H 9999


# also needed for the DIRAC integration, due to idiosyncrasies of the belle2 code
rucio scope add --account root --scope root
# the root container for the VO already needs to exist
rucio did add --type container -d /testvo.example.org
