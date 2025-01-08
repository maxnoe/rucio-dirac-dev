#!/usr/bin/env bash
set -euo pipefail

IFS=$'\n\t'

ulimit -n 1024

install_root="/opt/dirac/"
install_cfg="${install_root}/dirac-installation.cfg"
source "/opt/dirac/bashrc"

# Configure and set up the site
dirac-configure --cfg "${install_cfg}" ${DIRAC_CONFIGURE_OPTIONS:-}
dirac-setup-site ${DIRAC_SETUP_OPTIONS:-}
