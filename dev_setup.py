import os
import shlex
import subprocess as sp
import sys
import time
from argparse import ArgumentParser
from functools import partial
from pathlib import Path

RUCIO_SERVICES = [
    "rucio-db",
    "rucio-server",
    "rucio-storage-1",
    "rucio-storage-2",
    "rucio-storage-3",
    "rucio-conveyor-poller",
    "rucio-conveyor-submitter",
    "rucio-conveyor-finisher",
    "rucio-conveyor-evaluator",
    "fts",
    "ftsdb",
]

DIRAC_SERVICES = [
    "dirac-server",
    "dirac-ce",
    "dirac-db",
    "cvmfs-stratum0",
]

COMMON_SERVICES = [
    "clients",
]

# pass current user/group ids to compose
# so that users in containers have same uid/gid as
# the host to prevent permission issues in mounted volumes
# use a fixed id of 1000 in case host user is root, as in the kubernetes CI runner
current_uid = str(os.getuid())
current_gid = str(os.getgid())
os.environ["USERID"] = os.getenv(
    "USERID", current_uid if current_uid != "0" else "1000"
)
os.environ["GROUPID"] = os.getenv(
    "GROUPID", current_gid if current_gid != "0" else "1000"
)

def chmod_certs():
    # git does not store file permissions, but private keys need
    # to be only readable by the user
    for path in Path("certs").glob("*.key.pem"):
        path.chmod(0o600)

    for path in Path("certs/ssh").glob("*"):
        path.chmod(0o600)


def compose(args):
    cmd = ["docker", "compose"]
    cmd.extend(args)
    print(shlex.join(cmd))
    sp.run(cmd, check=True)


def compose_exec(service, *cmd, user=None):
    run = ["exec"]
    if user is not None:
        run.extend(["-u", user])
    run.append(service)
    run.extend(cmd)
    compose(run)


def compose_up(*services):
    cmd = [
        "up",
        "-d",
        "--build",
        *services,
    ]
    compose(cmd)


def compose_down(*services):
    cmd = [
        "down",
        "--remove-orphans",
        "--volumes",
        *services,
    ]
    compose(cmd)


def compose_cp(from_, to):
    compose(["cp", from_, to])


def any_running(*services):
    ret = sp.run(
        ["docker", "compose", "ps", "--format", "{{.Service}}"],
        capture_output=True,
        encoding="utf-8",
    )
    running_services = set(ret.stdout.splitlines())
    return len(running_services.intersection(services)) > 0


def setup_dirac(args):
    chmod_certs()
    if any_running(*DIRAC_SERVICES):
        print(
            "At least one DIRAC service is already running. Run teardown-dirac if you want to start fresh."
        )
        sys.exit(1)

    compose_up(*DIRAC_SERVICES, *COMMON_SERVICES)
    time.sleep(15)
    compose_exec("clients", "pip",  "install",  "-e", "/src/DIRAC", user="root")
    compose_exec("dirac-server", "pip",  "install",  "-e", "/src/DIRAC", user="root")
    compose(["restart", "dirac-server"])
    time.sleep(15)
    # dirac setup, the installation process needs the DB, so we cannot
    # run it already at image build time
    dirac_exec = partial(compose_exec, user="dirac:dirac")
    user_exec = partial(compose_exec, user="user:user")
    dirac_exec(
        "dirac-server",
        "/home/dirac/install_site.sh",
    )
    dirac_exec("dirac-server", "python", "configure.py", "resources.conf", "-c", "yes")
    user_exec("clients", "dirac-proxy-init", "--nocs")
    user_exec(
        "clients",
        "dirac-configure",
        "-C",
        "dips://dirac-server:9135/Configuration/Server",
        "-S",
        "Rucio-Tests",
    )
    user_exec("clients", "dirac-proxy-init", "-g", "dirac_admin")
    user_exec("clients", "dirac-admin-allow-site", "CTAO.CI.de", "add site")
    user_exec("clients", "dirac-proxy-destroy")
    for svc in ["SiteDirector", "PilotSyncAgent", "Optimizers"]:
        dirac_exec(
            "dirac-server",
            "dirac-restart-component",
            "WorkloadManagement",
            svc,
        )

    # cvmfs setup
    compose_exec(
        "cvmfs-stratum0", "cvmfs_server", "mkfs", "-o", "root", "testvo.example.org"
    )
    # install rucio cfg to cvmfs
    compose_exec("cvmfs-stratum0", "cvmfs_server", "transaction")
    # due to how overlay-fs works in docker and inside the container, we cannot just copy
    # the file using docker cp into the container into the /cvmfs/ directory.
    # Solution: copy to tmp, move in container.
    compose_cp("rucio/rucio_dirac_user.cfg", "cvmfs-stratum0:/tmp/rucio.cfg")
    compose_exec("cvmfs-stratum0", "mkdir", "-p", "/cvmfs/testvo.example.org/rucio/etc/")
    compose_exec(
        "cvmfs-stratum0", "mv", "/tmp/rucio.cfg", "/cvmfs/testvo.example.org/rucio/etc/"
    )
    compose_exec("cvmfs-stratum0", "cvmfs_server", "publish")


def setup_rucio(args):
    chmod_certs()
    if any_running(*RUCIO_SERVICES):
        print(
            "At least one RUCIO service is already running."
            " Run teardown-rucio if you want to start fresh."
        )
        sys.exit(1)

    # run database init first
    compose_up("rucio-db")
    compose(["run", "--rm", "rucio-init"])

    # then all the rest
    compose_up(*RUCIO_SERVICES, *COMMON_SERVICES)
    time.sleep(15)
    compose_exec("clients", "pip",  "install",  "-e", "/src/rucio", user="root")
    compose_exec("rucio-server", "pip",  "install",  "-e", "/src/rucio", user="root")
    compose(["restart", "rucio-server"])
    time.sleep(15)
    compose_exec("clients", "/setup_certificates.sh", user="root")
    compose_exec("clients", "/setup_rucio.sh")


def teardown_dirac(args):
    compose_down(*DIRAC_SERVICES)


def teardown_rucio(args):
    compose_down(*RUCIO_SERVICES)


def setup(args):
    setup_rucio(args)
    setup_dirac(args)


def teardown(args):
    compose_down()


parser = ArgumentParser()
subparsers = parser.add_subparsers(required=True)

parser_setup = subparsers.add_parser("setup", help="Run setup for all components")
parser_setup.set_defaults(func=setup)

parser_teardown = subparsers.add_parser("teardown", help="Cleanup all components")
parser_teardown.set_defaults(func=teardown)

parser_setup_dirac = subparsers.add_parser("setup-dirac", help="Run setup only for DIRAC")
parser_setup_dirac.set_defaults(func=setup_dirac)

parser_teardown_dirac = subparsers.add_parser("teardown-dirac", help="Cleanup only DIRAC")
parser_teardown_dirac.set_defaults(func=teardown_dirac)

parser_setup_rucio = subparsers.add_parser("setup-rucio", help="Run setup only for RUCIO")
parser_setup_rucio.set_defaults(func=setup_rucio)

parser_teardown_rucio = subparsers.add_parser(
    "teardown-rucio", help="Run cleanup only for RUCIO"
)
parser_teardown_rucio.set_defaults(func=teardown_rucio)


def main(args=None):
    args = parser.parse_args(args=args)
    if "USERID" not in os.environ or "GROUPID" not in os.environ:
        print("To silence warnings about USERID or GROUPID not being set, run:")
        print("  $ export USERID=$(id -u)")
        print("  $ export GROUPID=$(id -g)")
    args.func(args)


if __name__ == "__main__":
    main()
