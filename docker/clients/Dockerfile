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

ENV DIRAC_DIR="/home/user"
ENV DIRACOS="${DIRAC_DIR}/diracos"

RUN \
  if getent group ${GROUPID}; then \
    groupmod --new-name user $(getent group ${GROUPID} | cut -d: -f1); \
  else \
    groupadd --gid ${GROUPID} user; \
  fi\
  && adduser --uid ${USERID} --gid user -s /bin/bash -d /home/user user

RUN mkdir -p ${DIRAC_DIR} \
    && chown -R user:user ${DIRAC_DIR}

WORKDIR ${DIRAC_DIR}

# Install DIRAC client
USER user

COPY --from=builder /src/dist/*.whl /tmp/
RUN curl -LO https://github.com/DIRACGrid/DIRACOS2/releases/download/${DIRACOS_VERSION}/DIRACOS-Linux-x86_64.sh \
    && bash DIRACOS-Linux-x86_64.sh -p ${DIRAC_DIR}/diracos \
    && rm -f DIRACOS-Linux-x86_64.sh \
    && source ${DIRAC_DIR}/diracos/diracosrc \
    && micromamba install dirac-grid=${DIRAC_VERSION} rucio-clients==${RUCIO_VERSION} pytest \
    && pip install --no-cache-dir /tmp/*.whl

RUN mkdir -p ${DIRAC_DIR}/.globus \
    && mkdir -p ${DIRACOS}/etc/grid-security/certificates

ENV \
  CONDA_PREFIX="${DIRACOS}" \
  MAMBA_ROOT_PREFIX="${DIRACOS}" \
  CONDOR_CONFIG="${DIRACOS}/etc/condor/condor_config" \
  DAVIX_DISABLE_REDIRECT_CACHING=1 \
  DAVIX_USE_LIBCURL=1 \
  GSETTINGS_SCHEMA_DIR="${DIRACOS}/share/glib-2.0/schemas" \
  PATH="${DIRACOS}/bin:${DIRACOS}/condabin:${PATH}" \
  X509_CERT_DIR="${DIRACOS}/etc/grid-security/certificates" \
  X509_VOMSES="${DIRACOS}/etc/grid-security/vomses" \
  X509_VOMS_DIR="${DIRACOS}/etc/grid-security/vomsdir" \
  XML_CATALOG_FILES="file://${DIRACOS}/etc/xml/catalog file:///etc/xml/catalog" \
