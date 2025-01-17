# first stage, build policy package
FROM python:3.9 AS builder

ADD /policy /src/
RUN python -m pip install --no-cache build && python -m build --wheel /src/ 


FROM almalinux:9

ARG DIRACOS_VERSION="2.46"
ARG DIRAC_VERSION="8.0.62"
ARG RUCIO_VERSION="36.0.0.post2"
ARG USERID=1000
ARG GROUPID=1000

ENV DIRAC_DIR="/dirac/${DIRACOS_VERSION}"

RUN dnf install -y \
        procps \
        openssh-server \
        openssh-clients \
        epel-release \
        https://ecsft.cern.ch/dist/cvmfs/cvmfs-release/cvmfs-release-latest.noarch.rpm \
    && dnf install -y cvmfs \
    && cvmfs_config setup


ADD /docker/dirac/ce/testvo.example.org.conf /etc/cvmfs/config.d/testvo.example.org.conf
ADD /docker/dirac/ce/default.local /etc/cvmfs/default.local
Add /docker/dirac/ce/entrypoint.sh /entrypoint.sh

RUN cd /etc/ssh && ssh-keygen -A

RUN mkdir -p /etc/grid-security/certificates
RUN mkdir -p /etc/grid-security/vomsdir/testvo.example.org
RUN mkdir -p /etc/grid-security/vomses
RUN touch /etc/grid-security/vomses/testvo.example.org

RUN \
  if getent group ${GROUPID}; then \
    groupmod --new-name dirac $(getent group ${GROUPID} | cut -d: -f1); \
  else \
    groupadd --gid ${GROUPID} dirac; \
  fi\
  && adduser --uid ${USERID} --gid dirac -s /bin/bash -d /home/dirac dirac

RUN mkdir -p /home/dirac/.ssh && chown -R dirac:dirac /home/dirac

# Install DIRAC client
COPY --from=builder /src/dist/*.whl /tmp/
RUN mkdir -p ${DIRAC_DIR} \
    && curl -LO https://github.com/DIRACGrid/DIRACOS2/releases/download/${DIRACOS_VERSION}/DIRACOS-Linux-x86_64.sh \
    && bash DIRACOS-Linux-x86_64.sh -p ${DIRAC_DIR}/Linux-x86_64 \
    && rm -f DIRACOS-Linux-x86_64.sh \
    && source ${DIRAC_DIR}/Linux-x86_64/diracosrc \
    && pip install --no-cache-dir \
      DIRAC==${DIRAC_VERSION} \
      rucio-clients==${RUCIO_VERSION} \
      /tmp/*.whl \
    && ln -s ${DIRAC_DIR} /dirac/pro \
    && chown -R dirac:dirac /dirac


ENTRYPOINT ["/entrypoint.sh"]
