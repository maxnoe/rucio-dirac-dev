#!/bin/bash
# -*- coding: utf-8 -*-
# Copyright European Organization for Nuclear Research (CERN) since 2012
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
set -eu -o pipefail

function generate() {
  export PASSPHRASE=123456
  DAYS=9000

  # Development CA
  openssl genrsa -out test_ca.key.pem -passout env:PASSPHRASE 2048
  openssl req -x509 -new -batch -key test_ca.key.pem -days $DAYS -out test_ca.pem -subj "/CN=Test Development CA" -passin env:PASSPHRASE
  hash=$(openssl x509 -noout -hash -in test_ca.pem)
  ln -sf test_ca.pem $hash.0

  # Generate CRL
  touch index.txt
  echo 1000 > crlnumber
  openssl ca -config ../openssl_config_ca.cnf -keyfile test_ca.key.pem -cert test_ca.pem -gencrl -out test_ca.crl.r0

  # User certificate.
  openssl req -new -newkey rsa:2048 -noenc -keyout user.key.pem \
    -subj "/CN=Test User" \
    -addext "subjectAltName=email:test@example.org" \
    > user.csr
  openssl x509 -req -days $DAYS -CAcreateserial -extfile <(printf "keyUsage = critical, digitalSignature, keyEncipherment") -in user.csr -CA test_ca.pem -CAkey test_ca.key.pem -out user.pem
  cat "user.pem" "user.key.pem" > "user.certkey.pem"

  # Convert to p12 format, needed to access web DIRAC interface from the browser
  openssl pkcs12 -export -out user.p12 -in user.pem -inkey user.key.pem -password "pass:"

  # The service certificates
  for CN in rucio-server rucio-webui rucio-storage-1 rucio-storage-2 rucio-storage-3 dirac-server fts
  do
    SAN="subjectAltName=DNS:$CN,DNS:localhost"
    openssl req -new -newkey rsa:2048 -noenc -keyout "hostcert_$CN.key.pem" -subj "/CN=$CN" > "hostcert_$CN.csr"
    openssl x509 -req -days $DAYS -CAcreateserial -extfile <(printf "%s" "$SAN") -in "hostcert_$CN.csr" -CA test_ca.pem -CAkey test_ca.key.pem -out "hostcert_$CN.pem" -passin env:PASSPHRASE
  done

  cat "hostcert_rucio-server.pem" "hostcert_rucio-server.key.pem" > "hostcert_rucio-server.certkey.pem"

  rm ./*.csr

  # SSH server
  mkdir -p ssh
  rm -f ssh/diracuser_sshkey* && ssh-keygen -m PEM -t rsa -b 2048 -f ssh/diracuser_sshkey -C 'ssh keys' -N ""

  echo
  echo "ln -s test_ca.pem $hash.0"
  echo
}


mkdir certs || (echo "Directory certs already exists, please clean-up manually before running this script again" && exit 1)
(cd certs && generate)
