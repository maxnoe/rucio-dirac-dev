# rucio version used as base for the final image
ARG RUCIO_TAG=release-36.0.0.post2
ARG RUCIO_CONTAINER=undefined
ARG USER=root

# first stage, build policy package
FROM python:3.9 AS builder

ADD ../../policy /src/
RUN python -m pip install --no-cache build && python -m build --wheel /src/ 


# second stage, copy and install wheel
# We are using the official python 3.11 image
# as base image in the slim variant to reduce image size.
FROM rucio/rucio-${RUCIO_CONTAINER}:${RUCIO_TAG}

COPY --from=builder /src/dist/*.whl /tmp/

ARG RUCIO_CONTAINER
ARG RUCIO_TAG
ARG USER

# server and daemons use root, clients use "user", switch to root, install, then back
USER root
RUN dnf install -y --setopt=install_weak_deps=False git \
  && python3 -m pip install --no-cache-dir /tmp/*.whl \
  && dnf remove -y git \
  && dnf autoremove \
  && dnf clean all

USER ${USER}

ENV RUCIO_POLICY_PACKAGE=dirac_rucio_policy
