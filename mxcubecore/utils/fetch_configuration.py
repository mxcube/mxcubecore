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

"""Bootstrap a local checkout of the shared mxcube_configuration repository
(https://github.com/mxcube/mxcube_configuration) and print the
HardwareRepository lookup path (the value expected by ``-r`` in mxcubeweb
and mxcubeqt, or by the ``MXCUBE_CORE_CONFIG_PATH`` environment variable in
mxcubeqt) for a given consumer.

This is installed as the ``mxcube-fetch-config`` console script. Typical use::

    mxcubeweb-server -r "$(mxcube-fetch-config --for web)" --static-folder ui/build

See mxcubecore issue #944 for the motivation: the mockup/demo configuration
used to be duplicated (and drift out of sync) between mxcubecore, mxcubeweb
and mxcubeqt. mxcube_configuration is the single shared copy; this script is
the convenience layer for using it, so nobody has to hand-clone the repo and
hand-build the ":"-joined lookup path described in its README.
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
TARGETS = ("core", "web", "qt")


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
    if not (dest / ".git").is_dir():
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", ref, url, str(dest)],
            check=True,
        )
        return dest

    try:
        subprocess.run(
            ["git", "-C", str(dest), "fetch", "--depth", "1", "origin", ref],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(dest), "checkout", "FETCH_HEAD"], check=True
        )
    except subprocess.CalledProcessError:
        # The existing shallow clone can't reach `ref` (e.g. it was cloned
        # at a different tag/branch) - start over instead of trying to
        # unshallow it.
        shutil.rmtree(dest)
        return ensure_checkout(dest, ref, url)

    return dest


def build_lookup_path(dest: Path, target: str, gphl: bool = False) -> str:
    """Build the `-r` / MXCUBE_CORE_CONFIG_PATH value for `target`
    ("core", "web" or "qt"), pointing at the shared checkout in `dest`.

    "web" does not need its own `mxcube-web` entry in the path:
    `HardwareRepository.find_in_repository("mxcube-web")` finds that
    subdirectory under the shared root directly (mxcubeweb/__init__.py),
    and the two files in it (server.yaml, ui.yaml) are then read straight
    from that discovered directory, not through another lookup-path
    search - and neither name collides with a top-level file in demo.yaml,
    so there is nothing for it to override anyway.

    "qt" does need its `mxcube-qt` entry listed ahead of the shared root:
    mxcubeqt loads individual hardware object files (e.g. sample_view.yaml)
    through the generic lookup-path search, and `mxcube-qt/sample_view.yaml`
    is a genuine override of the shared demo.yaml/sample_view.yaml - it only
    takes effect if `mxcube-qt` is searched before the shared root.
    """
    if target not in TARGETS:
        raise ValueError(f"Unknown target {target!r}, expected one of {TARGETS}")

    shared = dest / "demo.yaml"
    parts = []
    if gphl:
        parts.append(shared / "gphl")
    if target == "qt":
        parts.append(shared / "mxcube-qt")
    parts.append(shared)

    return os.pathsep.join(str(part) for part in parts)


def parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch/update a local checkout of mxcube_configuration and "
            "print the HardwareRepository lookup path for it."
        )
    )
    parser.add_argument(
        "--for",
        dest="target",
        choices=TARGETS,
        default="core",
        help="Consumer to build the lookup path for (default: %(default)s).",
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
        "--gphl",
        action="store_true",
        help="Prepend the GPhL workflow configuration overrides to the path.",
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

    print(build_lookup_path(args.dest, args.target, args.gphl))
    return 0


if __name__ == "__main__":
    sys.exit(main())
