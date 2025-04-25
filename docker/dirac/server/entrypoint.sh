#!/bin/bash

env | grep DIRAC

if [[ ! -f /opt/dirac/setup_done ]]; then
  sudo -E -u dirac /home/dirac/install_site.sh
  sudo -E -u dirac bash -c '
    ssh-keyscan -H dirac-ce >> ~/.ssh/known_hosts

    source $DIRACOS/diracosrc
    python /home/dirac/configure.py /home/dirac/resources.conf -c yes

    # allow site exits with error status about
    # non-existent proxy even if local authentication works
    dirac-admin-allow-site "CTAO.CI.de" "test" -o /DIRAC/Security/UseServerCertificate=True || true

    dirac-restart-component WorkloadManagement SiteDirector
    dirac-restart-component WorkloadManagement PilotSyncAgent
    dirac-restart-component WorkloadManagement Optimizers
  '

  touch /opt/dirac/setup_done
fi

source $DIRACOS/diracosrc
/opt/dirac/sbin/runsvdir-start
