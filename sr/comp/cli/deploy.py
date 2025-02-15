"""
Deploy the compstate to its various deployments.

This is the canonical way to push a local compstate onto host machines;
specifically it will target those specified in the ``deployments.yaml`` file
within the compstate.

Compstates must not have local changes or untracked files (as reported by ``git
status``) and must be valid in order to be deployed.

During deployment, the states of the hosts relative to the current state are
checked and the user will be warned if:

-  the state of a host was unavailable (for example due to network errors)
-  the state of a host appears to be more recent than the current state (as
   determined by git ancestry)
-  the state of a host appears to be unrelated to the current state (again as
   determined by git ancestry)

In any case, the user is able to continue with the deployment interactively.
"""

from __future__ import annotations

import argparse
import io
import sys
import warnings
from contextlib import contextmanager
from typing import cast, Iterable, Iterator, TextIO, TYPE_CHECKING, TypeVar

from .deploy_api import CLIInteractions, UserInteractions

if TYPE_CHECKING:
    from sr.comp.raw_compstate import RawCompstate

T = TypeVar('T')

API_TIMEOUT_SECONDS = 3
DEPLOY_USER = 'srcomp'


@contextmanager
def exit_on_exception(
    interactions: UserInteractions[T],
    msg: str = '{0}',
    kind: type[Exception] = Exception,
) -> Iterator[None]:
    try:
        yield
    except kind as e:
        interactions.show_error(msg.format(e))
        # TODO(PR): interactions exit?
        exit(1)


@contextmanager
def guard_unicode_output(stream: TextIO) -> Iterator[None]:
    """
    Cope with users environments not being able to handle unicode by softening
    the display of characters they can't handle.

    While I would ideally prefer not to have this sort of behaviour, as it can
    happen mid-deploy (which we cannot roll back) it's far safer that we handle
    these _somehow_ than error the deploy part-way through.

    This is aimed at users running under certain Windows Subsystem for Linux
    Operating Systems which default to a non utf-8 locale :(
    """

    encoding = stream.encoding

    if encoding.lower() == 'utf-8':
        # Happy path
        yield
        return

    warnings.warn(
        "Your locale does not support unicode. Some characters may not display correctly.",
        stacklevel=1,
    )

    orig_write = stream.write

    def write(text: str, *a: object, **k: object) -> None:
        text = text.encode(encoding, errors='backslashreplace').decode(encoding)
        orig_write(text, *a, **k)

    try:
        stream.write = write  # type: ignore[method-assign, assignment]
        yield
    finally:
        stream.write = orig_write  # type: ignore[method-assign]


def query_warn(msg: object, interactions: UserInteractions[T]) -> None:
    if not interactions.query_bool(f"Warning: {msg}. Continue?", False):
        # TODO(PR): interactions exit?
        exit(1)


def ref_compstate(host: str) -> str:
    return f'ssh://{DEPLOY_USER}@{host}/~/compstate.git'


def deploy_to(
    compstate: RawCompstate,
    host: str,
    revision: str,
    verbose: bool,
    interactions: UserInteractions[T],
) -> int:
    interactions.show_strong(f"Deploying to {host}:")

    from fabric import Connection  # type: ignore[import-untyped]
    from invoke.exceptions import UnexpectedExit

    # Make connection early to check if host is up.
    with Connection(host, user=DEPLOY_USER) as connection:
        # Push the repo
        url = ref_compstate(host)
        # Make a new branch for this revision so that it's visible to
        # anything which fetches the repo; use the revision id in the
        # branch name to avoid race conditions without needing to come
        # up with our own unique identifier.
        # This also means we don't need to worry about whether or not the
        # revision exists in the target, since this push will simply no-op
        # if it's already present
        revspec = '{0}:refs/heads/deploy-{0}'.format(revision)
        with exit_on_exception(interactions, kind=RuntimeError):
            compstate.push(
                url,
                revspec,
                err_msg=f"Failed to push to {host}.",
            )

        cmd = f"./update '{revision}'"
        stdout, stderr = io.StringIO(), io.StringIO()
        try:
            result = connection.run(cmd, out_stream=stdout, err_stream=stderr)
        except UnexpectedExit as e:
            result = e.result

        retcode: int = result.exited

        if verbose or retcode != 0:
            interactions.show_buffer(stdout)

        interactions.show_buffer(stderr)

        return retcode


def get_deployments(compstate: RawCompstate, interactions: UserInteractions[T]) -> list[str]:
    with exit_on_exception(interactions, "Failed to get deployments from state ({0})."):
        return compstate.deployments


def get_current_state(host: str, interactions: UserInteractions[T]) -> str | None:
    import requests

    url = f'http://{host}/comp-api/state'
    try:
        response = requests.get(url, timeout=API_TIMEOUT_SECONDS)
        response.raise_for_status()
        raw_state = response.json()
    except Exception as e:
        # TODO(PR): Should this just raise and be handled in the level above?
        interactions.show_info(str(e))
        return None
    else:
        # While this could be any JSON, the schema is that this is a string
        # containing the commit hash of the compstate.
        return cast(str, raw_state['state'])


def check_host_state(
    compstate: RawCompstate,
    host: str,
    revision: str,
    verbose: bool,
    interactions: UserInteractions[T],
) -> bool:
    """
    Compares the host state to the revision we want to deploy. If the
    host's state isn't in the history of the deploy revision then various
    options are presented to the user.

    Returns whether or not to skip deploying to the host.
    """
    SKIP = True
    UPDATE = False
    if verbose:
        interactions.show_info(f"Checking host state for {host} (timeout {API_TIMEOUT_SECONDS} seconds).")
    state = get_current_state(host, interactions)
    if not state:
        if interactions.query_bool(
            f"Failed to get state for {host}, cannot advise about history. Deploy anyway?",
            True,
        ):
            return UPDATE
        else:
            return SKIP

    if state == revision:
        interactions.show_info(f"Host {host} already has requested revision ({revision[:8]})")
        return SKIP

    # Ideal case:
    if compstate.has_ancestor(state):
        return UPDATE

    # Check for unknown commit
    if not compstate.has_commit(state):
        if interactions.query_bool(f"Host {host} has unknown state '{state}'. Try to fetch it?", True):
            compstate.fetch('origin', quiet=True)
            compstate.fetch(ref_compstate(host), ('HEAD', state), quiet=True)

    # Old revision:
    if compstate.has_descendant(state):
        if interactions.query_bool(f"Host {host} has more recent state '{state}'. Deploy anyway?", True):
            return UPDATE
        else:
            return SKIP

    # Some other revision:
    if compstate.has_commit(state):
        if interactions.query_bool(f"Host {host} has sibling state '{state}'. Deploy anyway?", True):
            return UPDATE
        else:
            return SKIP

    # An unknown state
    if interactions.query_bool(f"Host {host} has unknown state '{state}'. Deploy anyway?", True):
        return UPDATE
    else:
        return SKIP


def require_no_changes(compstate: RawCompstate, interactions: UserInteractions[T]) -> None:
    if compstate.has_changes:
        interactions.show_error(
            "Cannot deploy state with local changes. "
            "Commit or remove them and re-run.",
        )
        interactions.show_info(
            compstate.git(['status'], return_output=True),
        )
        # TODO(PR): interactions exit?
        exit(1)


def require_valid(compstate: RawCompstate, interactions: UserInteractions[T]) -> None:
    from sr.comp.validation import validate

    with exit_on_exception(interactions, "State cannot be loaded: {0}"):
        comp = compstate.load()

    num_errors = validate(comp)
    if num_errors:
        query_warn("State has validation errors (see above)", interactions)


def run_deployments(
    args: argparse.Namespace,
    compstate: RawCompstate,
    hosts: Iterable[str],
    interactions: UserInteractions[T],
) -> None:
    revision = compstate.rev_parse('HEAD')
    for host in hosts:
        if not args.skip_host_check:
            skip_host = check_host_state(compstate, host, revision, args.verbose, interactions)
            if skip_host:
                interactions.show_strong(f"Skipping {host}.")
                continue

        retcode = deploy_to(compstate, host, revision, args.verbose, interactions)
        if retcode != 0:
            # TODO: work out if it makes sense to try to rollback here?
            interactions.show_error(f"Failed to deploy to '{host}' (exit status: {retcode}).")
            # TODO(PR): interactions exit?
            exit(retcode)

    interactions.show_strong_ok("Done")


def command(args: argparse.Namespace) -> None:
    from sr.comp.raw_compstate import RawCompstate

    interactions = CLIInteractions()

    with guard_unicode_output(sys.stdout), guard_unicode_output(sys.stderr):
        compstate = RawCompstate(args.compstate, local_only=False)
        hosts = get_deployments(compstate, interactions)

        require_no_changes(compstate, interactions)
        require_valid(compstate, interactions)

        run_deployments(args, compstate, hosts, interactions)


def add_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument(
        '--skip-host-check',
        action='store_true',
        help="skips checking the current state of the hosts",
    )


def add_subparser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    help_msg, *_ = __doc__.strip().splitlines()
    parser = subparsers.add_parser(
        'deploy',
        help=help_msg,
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_options(parser)
    parser.add_argument('compstate', help="competition state repository")
    parser.set_defaults(func=command)
