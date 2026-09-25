# encoding: utf-8
#
#  Project name: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.
"""Test suite for mxcubecore.utils.fetch_configuration"""

import os
import subprocess

import pytest

from mxcubecore.utils.fetch_configuration import (
    build_lookup_path,
    default_dest,
    ensure_checkout,
    main,
)


def test_default_dest_honours_mxcube_config_home(monkeypatch, tmp_path):
    monkeypatch.setenv("MXCUBE_CONFIG_HOME", str(tmp_path / "custom"))
    assert default_dest() == tmp_path / "custom"


def test_default_dest_honours_xdg_cache_home(monkeypatch, tmp_path):
    monkeypatch.delenv("MXCUBE_CONFIG_HOME", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert default_dest() == tmp_path / "mxcube" / "mxcube_configuration"


def test_default_dest_falls_back_to_home_cache(monkeypatch, tmp_path):
    monkeypatch.delenv("MXCUBE_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setattr(
        "mxcubecore.utils.fetch_configuration.Path.home", lambda: tmp_path
    )
    assert default_dest() == tmp_path / ".cache" / "mxcube" / "mxcube_configuration"


@pytest.mark.parametrize(
    ("paths", "expected_parts"),
    [
        (["demo.yaml"], ["demo.yaml"]),
        # A beamline's own directory (mxcubecore issue #1226) instead of
        # the demo/mockup one - no "mxcube-web" needed either:
        # HardwareRepository.find_in_repository locates it under whatever
        # directory is already in the path on its own.
        (["id30a1"], ["id30a1"]),
        # Chaining a subdirectory (e.g. the GPhL workflow overrides) onto
        # a root directory, in the given order.
        (["id30a1", "id30a1/gphl"], ["id30a1", "id30a1/gphl"]),
        (["demo.yaml/mxcube-qt", "demo.yaml"], ["demo.yaml/mxcube-qt", "demo.yaml"]),
    ],
)
def test_build_lookup_path(tmp_path, paths, expected_parts):
    path = build_lookup_path(tmp_path, paths)
    expected = os.pathsep.join(
        str(tmp_path.joinpath(*part.split("/"))) for part in expected_parts
    )
    assert path == expected


@pytest.mark.parametrize(
    "bad_path", ["", ".", "..", "id30a1/..", "/etc", "id30a1//gphl"]
)
def test_build_lookup_path_rejects_invalid_entries(tmp_path, bad_path):
    with pytest.raises(ValueError):
        build_lookup_path(tmp_path, [bad_path])


@pytest.fixture
def fake_git(mocker):
    """Fix the resolved `git` executable path so assertions don't depend
    on where git happens to live on the machine running the tests.
    """
    git_path = "/usr/bin/git"
    mocker.patch(
        "mxcubecore.utils.fetch_configuration._git_executable", return_value=git_path
    )
    return git_path


def test_ensure_checkout_clones_when_missing(mocker, tmp_path, fake_git):
    dest = tmp_path / "mxcube_configuration"
    run = mocker.patch("subprocess.run")

    result = ensure_checkout(dest, ref="main", url="https://example.invalid/repo.git")

    assert result == dest
    run.assert_called_once_with(
        [
            fake_git,
            "clone",
            "--depth",
            "1",
            "--branch",
            "main",
            "https://example.invalid/repo.git",
            str(dest),
        ],
        check=True,
    )


def test_ensure_checkout_updates_existing_clone(mocker, tmp_path, fake_git):
    dest = tmp_path / "mxcube_configuration"
    (dest / ".git").mkdir(parents=True)
    run = mocker.patch("subprocess.run")

    ensure_checkout(dest, ref="v2", url="https://example.invalid/repo.git")

    assert run.call_count == 2
    fetch_call, checkout_call = run.call_args_list
    assert fetch_call.args[0] == [
        fake_git,
        "-C",
        str(dest),
        "fetch",
        "--depth",
        "1",
        "origin",
        "v2",
    ]
    assert checkout_call.args[0] == [
        fake_git,
        "-C",
        str(dest),
        "checkout",
        "FETCH_HEAD",
    ]


def test_ensure_checkout_reclones_on_unreachable_ref(mocker, tmp_path, fake_git):
    dest = tmp_path / "mxcube_configuration"
    (dest / ".git").mkdir(parents=True)
    (dest / "stale-file").touch()

    call_count = {"n": 0}

    def fake_run(cmd, check):
        call_count["n"] += 1
        if cmd[3] == "fetch":
            raise subprocess.CalledProcessError(1, cmd)
        return mocker.Mock()

    mocker.patch("subprocess.run", side_effect=fake_run)

    ensure_checkout(dest, ref="v3", url="https://example.invalid/repo.git")

    # The stale shallow clone should have been wiped and re-cloned from scratch.
    assert not (dest / "stale-file").exists()


def test_main_prints_lookup_path_default(mocker, tmp_path, capsys):
    dest = tmp_path / "mxcube_configuration"
    (dest / "demo.yaml" / "mxcube-web").mkdir(parents=True)

    # No --for given: defaults to ["demo.yaml"].
    exit_code = main(["--dest", str(dest), "--no-fetch"])

    assert exit_code == 0
    out = capsys.readouterr().out.strip()
    assert out == str(dest / "demo.yaml")


def test_main_prints_lookup_path_for_chained_dirs(mocker, tmp_path, capsys):
    dest = tmp_path / "mxcube_configuration"
    (dest / "demo.yaml" / "mxcube-qt").mkdir(parents=True)

    exit_code = main(
        ["--for", "demo.yaml/mxcube-qt", "demo.yaml", "--dest", str(dest), "--no-fetch"]
    )

    assert exit_code == 0
    out = capsys.readouterr().out.strip()
    assert out == os.pathsep.join(
        [str(dest / "demo.yaml" / "mxcube-qt"), str(dest / "demo.yaml")]
    )


def test_main_prints_lookup_path_for_beamline_dir(mocker, tmp_path, capsys):
    dest = tmp_path / "mxcube_configuration"
    (dest / "id30a1" / "gphl").mkdir(parents=True)

    exit_code = main(
        ["--for", "id30a1", "id30a1/gphl", "--dest", str(dest), "--no-fetch"]
    )

    assert exit_code == 0
    out = capsys.readouterr().out.strip()
    assert out == os.pathsep.join([str(dest / "id30a1"), str(dest / "id30a1" / "gphl")])


def test_main_honours_mxcube_config_for_env_var(monkeypatch, tmp_path, capsys):
    dest = tmp_path / "mxcube_configuration"
    (dest / "id30b" / "gphl").mkdir(parents=True)
    monkeypatch.setenv("MXCUBE_CONFIG_FOR", f"id30b{os.pathsep}id30b/gphl")

    exit_code = main(["--dest", str(dest), "--no-fetch"])

    assert exit_code == 0
    out = capsys.readouterr().out.strip()
    assert out == os.pathsep.join([str(dest / "id30b"), str(dest / "id30b" / "gphl")])


def test_main_no_fetch_requires_existing_dest(tmp_path, capsys):
    dest = tmp_path / "does-not-exist"

    exit_code = main(["--dest", str(dest), "--no-fetch"])

    assert exit_code == 1
    assert "does not exist" in capsys.readouterr().err


def test_main_reports_invalid_for_path_cleanly(tmp_path, capsys):
    exit_code = main(
        ["--for", "id30a1/../../etc", "--dest", str(tmp_path), "--no-fetch"]
    )

    assert exit_code == 1
    assert "id30a1/../../etc" in capsys.readouterr().err
