#!/bin/bash

env | grep DIRAC

if [[ ! -f /opt/dirac/setup_done ]]; then
  sudo -E -u dirac /home/dirac/install_site.sh
  sudo -E -u dirac bash -c '
    source $DIRACOS/diracosrc
    python /home/dirac/configure.py /home/dirac/resources.conf -c yes
  '

  touch /opt/dirac/setup_done
fi

/opt/dirac/sbin/runsvdir-start
