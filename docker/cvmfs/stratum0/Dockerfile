FROM almalinux:9

VOLUME ["/var/spool/cvmfs"]
VOLUME ["/srv/cvmfs"]

RUN dnf -y install epel-release https://ecsft.cern.ch/dist/cvmfs/cvmfs-release/cvmfs-release-latest.noarch.rpm \
    && dnf install -y cvmfs cvmfs-server httpd bzip2 \
    && systemctl enable httpd

CMD ["/usr/sbin/init"]
