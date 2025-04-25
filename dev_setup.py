import os
import shlex
import subprocess as sp
import sys
import time
from argparse import ArgumentParser
from functools import partial
from pathlib import Path
import logging

log = logging.getLogger("rucio-dirac-dev")


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
    log.info(shlex.join(cmd))
    sp.run(cmd, check=True)


def compose_exec(service, *cmd, user=None):
    run = ["exec"]
    if user is not None:
        run.extend(["-u", user])
    run.append(service)
    run.extend(cmd)
    compose(run)


def symlink_rucio_setup(client=False):
    repo = os.getenv("RUCIO_REPOSITORY")
    if repo is None:
        return
    
    link = Path(repo) / "setup.py"
    if link.exists() or link.is_symlink():
        link.unlink()

    if client:
        link.symlink_to("setup_rucio_client.py")
    else:
        link.symlink_to("setup_rucio.py")


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

    if len(services) == 0:
        return len(running_services) > 0

    return len(running_services.intersection(services)) > 0


def setup(args):
    if args.rucio is not None:
        log.info(f"Using rucio repository in {args.rucio}")
        os.environ["RUCIO_REPOSITORY"] = str(args.rucio.absolute())

    if args.dirac is not None:
        log.info(f"Using DIRAC repository in {args.dirac}")
        os.environ["DIRAC_REPOSITORY"] = str(args.dirac.absolute())

    chmod_certs()
    if any_running():
        log.info(
            "At least one service is already running."
            " Run teardown if you want to start fresh."
        )

    # run database init first
    compose_up("rucio-db")
    compose(["run", "--rm", "rucio-init"])

    # then all the rest
    compose_up(*RUCIO_SERVICES, *DIRAC_SERVICES, *COMMON_SERVICES)
    time.sleep(15)

    if os.getenv("RUCIO_REPOSITORY"):
        symlink_rucio_setup(client=True)
        compose_exec("clients", "pip",  "install",  "-e", "/src/rucio")
        compose_exec("dirac-server", "pip",  "install",  "-e", "/src/rucio", user="root")

        symlink_rucio_setup(client=False)
        compose_exec("rucio-server", "pip",  "install",  "-e", "/src/rucio", user="root")
        compose(["restart", "rucio-server"])

        time.sleep(15)

    compose_exec("clients", "/setup_certificates.sh", user="root")
    compose_exec("clients", "/setup_rucio.sh")

    # dev setup
    if os.getenv("DIRAC_REPOSITORY"):
        compose_exec("clients", "pip",  "install",  "-e", "/src/DIRAC", user="root")
        compose_exec("dirac-server", "pip",  "install",  "-e", "/src/DIRAC", user="root")

    if os.getenv("RUCIO_REPOSITORY") or os.getenv("DIRAC_REPOSITORY"):
        compose(["restart", "dirac-server"])
        time.sleep(15)


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



def teardown(args):
    compose_down()

common = ArgumentParser(add_help=False)
common.add_argument("--rucio", type=Path, help="Path to rucio repository for development")
common.add_argument("--dirac", type=Path, help="Path to DIRAC repository for development")

parser = ArgumentParser()
subparsers = parser.add_subparsers(required=True)

parser_setup = subparsers.add_parser("setup", help="Run setup for all components", parents=[common])
parser_setup.set_defaults(func=setup)

parser_teardown = subparsers.add_parser("teardown", help="Cleanup all components")
parser_teardown.set_defaults(func=teardown)


def main(args=None):
    logging.basicConfig(level=logging.INFO)
    args = parser.parse_args(args=args)
    if "USERID" not in os.environ or "GROUPID" not in os.environ:
        log.info("To silence warnings about USERID or GROUPID not being set, run:")
        log.info("  $ export USERID=$(id -u)")
        log.info("  $ export GROUPID=$(id -g)")
    args.func(args)


if __name__ == "__main__":
    main()
