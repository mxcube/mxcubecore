# encoding: utf-8
#
# License:
#
# This file is part of MXCuBE.
#
# MXCuBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MXCuBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with MXCuBE. If not, see <https://www.gnu.org/licenses/>.

"""Bootstrap a local checkout of a shared mxcube configuration repository
for instance: (https://github.com/mxcube/mxcube_configuration) and print the
HardwareRepository lookup path (the value expected by ``-r`` in mxcubeweb
and mxcubeqt, or by the ``MXCUBE_CORE_CONFIG_PATH`` environment variable in
mxcubeqt.

Installed as the ``mxcube-fetch-config`` console script. Example::

    mxcubeweb-server -r "$(mxcube-fetch-config)" --static-folder ui/build

mxcube_configuration holds one directory per "root" configuration - either
"demo.yaml" (the mockup/demo configuration) or a beamline's own directory,
e.g. "[beamlinename]". Each root directory can have optional subdirectories
holding additional/override configuration, e.g. "gphl" for the GPhL
workflow, or "mxcube-qt" for mxcubeqt-specific overrides - and possibly
others not yet in the repository, such as "plate" or "harvester".

--for takes one or more of these directories, each given relative to the
mxcube_configuration checkout, and joins them into the lookup path in the
order given, e.g.::

    mxcube-fetch-config --for demo.yaml
    mxcube-fetch-config --for [beamlinename]
    mxcube-fetch-config --for [beamlinename] [beamlinename]/gphl
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

DEFAULT_REPO_URL = "https://github.com/mxcube/mxcube_configuration.git"
DEFAULT_REF = "main"
DEFAULT_ROOT = "demo.yaml"


def _git_executable() -> str:
    """Resolve an absolute path to the `git` executable.

    subprocess calls are run with the full path (rather than the bare
    string "git") so that the executable actually invoked isn't affected
    by PATH lookup at call time.
    """
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("git executable not found on PATH")
    return git


def default_dest() -> Path:
    """Where to keep the local checkout, absent an explicit --dest.

    Honours $MXCUBE_CONFIG_HOME first, then the XDG cache convention, so
    mxcubecore, mxcubeweb and mxcubeqt can all share a single checkout
    instead of each keeping their own copy.
    """
    config_home = os.environ.get("MXCUBE_CONFIG_HOME")
    if config_home:
        return Path(config_home)
    xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
    cache_home = Path(xdg_cache_home) if xdg_cache_home else Path.home() / ".cache"
    return cache_home / "mxcube" / "mxcube_configuration"


def ensure_checkout(
    dest: Path, ref: str = DEFAULT_REF, url: str = DEFAULT_REPO_URL
) -> Path:
    """Make sure `dest` holds a checkout of `url` at `ref`, cloning or
    updating it as needed. Returns `dest`.
    """
    git = _git_executable()

    if not (dest / ".git").is_dir():
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [git, "clone", "--depth", "1", "--branch", ref, url, str(dest)],
            check=True,
        )
        return dest

    try:
        subprocess.run(
            [git, "-C", str(dest), "fetch", "--depth", "1", "origin", ref],
            check=True,
        )
        subprocess.run([git, "-C", str(dest), "checkout", "FETCH_HEAD"], check=True)
    except subprocess.CalledProcessError:
        # The existing shallow clone can't reach `ref` (e.g. it was cloned
        # at a different tag/branch) - start over instead of trying to
        # unshallow it.
        shutil.rmtree(dest)
        return ensure_checkout(dest, ref, url)

    return dest


def _validate_relative_path(rel: str) -> None:
    """Reject anything that isn't a plain, relative, "/"-separated path
    inside the mxcube_configuration checkout - used for each `--for`
    entry, so a stray absolute path or ".." can't escape the checkout.
    """
    if not rel:
        raise ValueError("--for path must not be empty")
    if rel.startswith("/") or (os.altsep and rel.startswith(os.altsep)):
        raise ValueError(f"--for path must be relative, got {rel!r}")
    segments = rel.split("/")
    if any(segment in ("", ".", "..") for segment in segments):
        raise ValueError(
            f"--for path must not contain '.', '..' or empty segments: {rel!r}"
        )


def build_lookup_path(dest: Path, paths: list) -> str:
    """Build the `-r` / MXCUBE_CORE_CONFIG_PATH value by joining one or
    more directories from `paths`, each given relative to the shared
    mxcube_configuration checkout in `dest`, in the given search order.

    Directories are typically:
      - a root directory holding the main configuration files: either
        "demo.yaml" (the mockup/demo configuration) or a beamline's own
        directory (e.g. "[beamlinename]").
      - optional subdirectories of that root holding additional/override
        configuration, e.g. "<root>/gphl" for the GPhL workflow, or
        "<root>/mxcube-qt" for mxcubeqt-specific overrides.

    mxcubeweb does not need its own "<root>/mxcube-web" listed explicitly:
    `HardwareRepository.find_in_repository("mxcube-web")` finds it under
    any directory already in the path (mxcubeweb/__init__.py), and the two
    files in it (server.yaml, ui.yaml) are then read straight from that
    discovered directory, not through another lookup-path search.

    List an override directory before the directory whose files it
    overrides, if the two can contain identically-named files (e.g.
    "<root>/mxcube-qt" before "<root>", since mxcubeqt loads individual
    hardware object files - such as sample_view.yaml - through the
    generic lookup-path search, and `find_in_repository` returns the
    first match) - `paths` is used exactly in the order given.
    """
    resolved = []
    for rel in paths:
        _validate_relative_path(rel)
        resolved.append(dest.joinpath(*rel.split("/")))

    return os.pathsep.join(str(part) for part in resolved)


def parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch/update a local checkout of mxcube_configuration and "
            "print the HardwareRepository lookup path for it."
        )
    )
    env_for = os.environ.get("MXCUBE_CONFIG_FOR")
    default_for = env_for.split(os.pathsep) if env_for else [DEFAULT_ROOT]
    parser.add_argument(
        "--for",
        dest="paths",
        nargs="+",
        metavar="DIR",
        default=default_for,
        help=(
            "One or more directories, relative to the mxcube_configuration "
            "checkout, to join into the lookup path, in search order "
            "(default: %(default)s, or $MXCUBE_CONFIG_FOR). E.g. "
            "'demo.yaml' for the mockup/demo configuration, '[beamlinename]' "
            "for a beamline's own directory, or "
            "'[beamlinename] [beamlinename]/gphl' to also include its GPhL "
            "workflow overrides."
        ),
    )
    parser.add_argument(
        "--ref",
        default=os.environ.get("MXCUBE_CONFIG_REF", DEFAULT_REF),
        help=(
            "Branch or tag of mxcube_configuration to check out (default: "
            "%(default)s, or $MXCUBE_CONFIG_REF). Pin this to a tag for CI "
            "and released versions instead of tracking a branch."
        ),
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=default_dest(),
        help=(
            "Directory to clone/update mxcube_configuration into (default: "
            "$MXCUBE_CONFIG_HOME, $XDG_CACHE_HOME/mxcube/mxcube_configuration "
            "or ~/.cache/mxcube/mxcube_configuration)."
        ),
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("MXCUBE_CONFIG_URL", DEFAULT_REPO_URL),
        help="URL of the mxcube_configuration repository.",
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Do not touch the network; use --dest as-is (it must already exist).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    args = parse_args(argv)

    if args.no_fetch:
        if not args.dest.is_dir():
            print(
                f"error: {args.dest} does not exist and --no-fetch was given",
                file=sys.stderr,
            )
            return 1
    else:
        ensure_checkout(args.dest, args.ref, args.url)

    try:
        lookup_path = build_lookup_path(args.dest, args.paths)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(lookup_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
