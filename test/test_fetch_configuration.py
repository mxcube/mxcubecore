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
    ("target", "gphl", "expected_parts"),
    [
        ("core", False, ["demo.yaml"]),
        # "web" needs no dedicated entry: HardwareRepository.find_in_repository
        # locates demo.yaml/mxcube-web on its own, and none of its files
        # (server.yaml, ui.yaml) override anything at the top level.
        ("web", False, ["demo.yaml"]),
        ("qt", False, ["demo.yaml/mxcube-qt", "demo.yaml"]),
        ("web", True, ["demo.yaml/gphl", "demo.yaml"]),
    ],
)
def test_build_lookup_path(tmp_path, target, gphl, expected_parts):
    path = build_lookup_path(tmp_path, target, gphl=gphl)
    expected = os.pathsep.join(str(tmp_path / part) for part in expected_parts)
    assert path == expected


def test_build_lookup_path_rejects_unknown_target(tmp_path):
    with pytest.raises(ValueError):
        build_lookup_path(tmp_path, "not-a-real-target")


def test_ensure_checkout_clones_when_missing(mocker, tmp_path):
    dest = tmp_path / "mxcube_configuration"
    run = mocker.patch("subprocess.run")

    result = ensure_checkout(dest, ref="main", url="https://example.invalid/repo.git")

    assert result == dest
    run.assert_called_once_with(
        [
            "git",
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


def test_ensure_checkout_updates_existing_clone(mocker, tmp_path):
    dest = tmp_path / "mxcube_configuration"
    (dest / ".git").mkdir(parents=True)
    run = mocker.patch("subprocess.run")

    ensure_checkout(dest, ref="v2", url="https://example.invalid/repo.git")

    assert run.call_count == 2
    fetch_call, checkout_call = run.call_args_list
    assert fetch_call.args[0] == [
        "git",
        "-C",
        str(dest),
        "fetch",
        "--depth",
        "1",
        "origin",
        "v2",
    ]
    assert checkout_call.args[0] == ["git", "-C", str(dest), "checkout", "FETCH_HEAD"]


def test_ensure_checkout_reclones_on_unreachable_ref(mocker, tmp_path):
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


def test_main_prints_lookup_path_without_network(mocker, tmp_path, capsys):
    dest = tmp_path / "mxcube_configuration"
    (dest / "demo.yaml" / "mxcube-web").mkdir(parents=True)

    exit_code = main(["--for", "web", "--dest", str(dest), "--no-fetch"])

    assert exit_code == 0
    out = capsys.readouterr().out.strip()
    assert out == str(dest / "demo.yaml")


def test_main_prints_lookup_path_for_qt(mocker, tmp_path, capsys):
    dest = tmp_path / "mxcube_configuration"
    (dest / "demo.yaml" / "mxcube-qt").mkdir(parents=True)

    exit_code = main(["--for", "qt", "--dest", str(dest), "--no-fetch"])

    assert exit_code == 0
    out = capsys.readouterr().out.strip()
    assert out == os.pathsep.join(
        [str(dest / "demo.yaml" / "mxcube-qt"), str(dest / "demo.yaml")]
    )


def test_main_no_fetch_requires_existing_dest(tmp_path, capsys):
    dest = tmp_path / "does-not-exist"

    exit_code = main(["--for", "core", "--dest", str(dest), "--no-fetch"])

    assert exit_code == 1
    assert "does not exist" in capsys.readouterr().err
