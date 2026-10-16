"""Check the hardware object configuration files before loading them.

Starting from the beamline configuration file, all the files referred to are
checked, the same way as they are loaded by the HardwareRepository:

- the files are syntactically correct YAML or XML,
- the hardware object class can be imported,
- the files referred to (objects, href) exist,
- the configuration is valid according to the HOConfig model of the class,
- the command and channel (tango, exporter, ...) sections are valid.

Properties not declared in a HOConfig model are reported as warnings
(errors with strict validation).

Usage, from the command line::

    mxcubecore-check-config -r <configuration directory>[:<directory>...]

or from Python::

    check = check_configuration(lookup_path)
    print(check.report())
"""

from __future__ import annotations

import argparse
import importlib
import os
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pydantic
from ruamel.yaml import YAML
from ruamel.yaml.error import MarkedYAMLError

from mxcubecore.BaseHardwareObjects import ConfiguredObject

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"

# Same file names and YAML settings as HardwareRepository
BEAMLINE_CONFIG_FILES = ("beamline.yaml", "beamline_config.yml")
_yaml = YAML(typ="safe", pure=True)

TOP_LEVEL_KEYS = {"class", "configuration", "objects"}


def _protocol_models() -> dict[str, Any]:
    from mxcubecore.model.protocols.epics import EpicsConfig
    from mxcubecore.model.protocols.exporter import ExporterConfig
    from mxcubecore.model.protocols.sardana import SardanaConfig
    from mxcubecore.model.protocols.tango import TangoConfig

    return {
        "tango": TangoConfig,
        "exporter": ExporterConfig,
        "epics": EpicsConfig,
        "sardana": SardanaConfig,
        "bluesky_http_server": None,
    }


@dataclass
class Problem:
    severity: str  # "error" or "warning"
    file: str
    message: str


@dataclass
class ConfigurationCheck:
    """Result of a configuration check"""

    lookup_path: list[str]
    strict: bool = False
    problems: list[Problem] = field(default_factory=list)
    checked_files: list[str] = field(default_factory=list)

    # ---------------------------------------------------------------- result
    def add_error(self, file: str, message: str) -> None:
        self.problems.append(Problem("error", str(file), message))

    def add_warning(self, file: str, message: str) -> None:
        self.problems.append(Problem("warning", str(file), message))

    @property
    def errors(self) -> list[Problem]:
        return [p for p in self.problems if p.severity == "error"]

    @property
    def warnings(self) -> list[Problem]:
        return [p for p in self.problems if p.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def report(self) -> str:
        """Human readable report"""
        lines = [f"Configuration directory: {self.lookup_path[0]}"]
        lines += [f"  also looking in: {p}" for p in self.lookup_path[1:]]
        lines.append(f"Checked {len(self.checked_files)} configuration files")

        by_file = defaultdict(list)
        for p in self.problems:
            by_file[p.file].append(p)
        for file, problems in by_file.items():
            lines.append(f"  {file}:")
            lines += [f"    {p.severity.upper()}: {p.message}" for p in problems]

        if not self.problems:
            lines.append("Configuration files OK")
        elif self.ok:
            lines.append(
                f"Configuration files OK, with {len(self.warnings)} warning(s)"
            )
        else:
            lines.append(
                f"Configuration files have {len(self.errors)} error(s)"
                f" and {len(self.warnings)} warning(s)"
            )
        return "\n".join(lines)

    # ---------------------------------------------------------------- files
    def find(self, relative_path: str) -> Path | None:
        """As HardwareRepository.find_in_repository"""
        relative_path = relative_path.lstrip(os.path.sep)
        for directory in self.lookup_path:
            path = Path(directory, relative_path)
            if path.exists():
                return path.absolute()
        return None

    def display_name(self, path: Path) -> str:
        for directory in self.lookup_path:
            try:
                return str(path.relative_to(Path(directory).absolute()))
            except ValueError:
                pass
        return str(path)

    # ---------------------------------------------------------------- check
    def run(self) -> ConfigurationCheck:
        beamline_file = next(
            (f for f in BEAMLINE_CONFIG_FILES if self.find(f) is not None), None
        )
        if beamline_file is None:
            self.add_error(
                self.lookup_path[0],
                f"no beamline configuration file ({', '.join(BEAMLINE_CONFIG_FILES)})",
            )
            return self

        self._seen: set[Path] = set()
        self._check_yaml(self.find(beamline_file))
        return self

    def _check_yaml(self, path: Path) -> None:
        if path in self._seen:
            return
        self._seen.add(path)
        name = self.display_name(path)
        self.checked_files.append(name)

        try:
            with path.open() as f:
                data = _yaml.load(f)
        except MarkedYAMLError as ex:
            mark = ex.problem_mark or ex.context_mark
            where = f"line {mark.line + 1}, column {mark.column + 1}: " if mark else ""
            self.add_error(name, f"YAML syntax error, {where}{ex.problem or ex}")
            return
        except Exception as ex:  # noqa: BLE001
            self.add_error(name, f"cannot read file: {ex}")
            return

        if not isinstance(data, dict):
            self.add_error(
                name, "the file must contain a mapping (class, configuration, objects)"
            )
            return

        protocols = _protocol_models()
        for key in data:
            if key not in TOP_LEVEL_KEYS and key not in protocols:
                self.add_warning(
                    name,
                    f"unknown top level key '{key}' (ignored), expected one of"
                    f" {', '.join(sorted(TOP_LEVEL_KEYS | set(protocols)))}",
                )

        cls = self._import_class(name, data.get("class"), yaml_style=True)

        configuration = data.get("configuration") or {}
        if not isinstance(configuration, dict):
            self.add_error(name, "'configuration' must be a mapping")
        elif cls is not None:
            self._validate(name, cls, configuration)

        for protocol, model in protocols.items():
            if model is not None and data.get(protocol) is not None:
                try:
                    model.model_validate(data[protocol])
                except pydantic.ValidationError as ex:
                    for msg in _format_errors(ex, prefix=protocol):
                        self.add_error(name, msg)

        objects = data.get("objects") or {}
        if isinstance(objects, list):  # !!omap
            objects = dict(
                o if isinstance(o, tuple) else next(iter(o.items())) for o in objects
            )
        if not isinstance(objects, dict):
            self.add_error(name, "'objects' must be a mapping of role: file")
            return
        for role, file_name in objects.items():
            self._check_reference(name, f"objects.{role}", str(file_name))

    def _check_reference(self, name: str, where: str, file_name: str) -> None:
        path = self.find(file_name)
        if path is None:
            self.add_error(name, f"{where}: file '{file_name}' not found")
        elif path.suffix in (".yaml", ".yml"):
            self._check_yaml(path)
        elif path.suffix == ".xml":
            self._check_xml(path)
        else:
            self.add_error(name, f"{where}: '{file_name}' is not a .yaml or .xml file")

    def _check_xml(self, path: Path) -> None:
        if path in self._seen:
            return
        self._seen.add(path)
        name = self.display_name(path)
        self.checked_files.append(name)

        try:
            # local configuration files, as parsed by the hardware repository
            root = ET.parse(path).getroot()  # noqa: S314
        except ET.ParseError as ex:
            line, column = ex.position
            reason = str(ex).split(": line ")[0]
            self.add_error(
                name, f"XML syntax error, line {line}, column {column + 1}: {reason}"
            )
            return

        if root.get("href") and not root.get("class"):
            # redirection to another file
            self._check_xml_href(name, root.get("href"))
            return

        cls = self._import_class(name, root.get("class"), yaml_style=False)
        if cls is not None:
            self._validate(name, cls, xml_configuration(root))

        for el in root.iter():
            if el is root:
                continue
            href = el.get("href") or el.get("hwrid")
            if href:
                self._check_xml_href(name, href, el.get("role"))

    def _check_xml_href(self, name: str, href: str, role: str | None = None) -> None:
        stem = href.strip().lstrip("/")
        where = f"role '{role}'" if role else "href"
        if self.find(stem + ".xml") is not None:
            self._check_xml(self.find(stem + ".xml"))
        elif self.find(stem + ".yaml") is None:
            # A yaml configured object is found if loaded before (by name)
            self.add_error(name, f"{where}: '{href}' not found ({stem}.xml)")

    def _import_class(self, name: str, class_path: Any, yaml_style: bool):
        if not class_path or not isinstance(class_path, str):
            self.add_error(name, "no 'class' given")
            return None
        class_path = class_path.strip()
        if yaml_style:
            if "." not in class_path:
                self.add_error(
                    name, f"class '{class_path}' must be given as module.Class"
                )
                return None
            module_name, class_name = class_path.rsplit(".", 1)
        else:
            module_name, class_name = class_path, class_path.split(".")[-1]
        try:
            module = importlib.import_module(module_name)
        except Exception as ex:  # noqa: BLE001
            self.add_error(
                name,
                f"cannot import module '{module_name}' for class '{class_path}':"
                f" {type(ex).__name__}: {ex}",
            )
            return None
        cls = getattr(module, class_name, None)
        if cls is None:
            self.add_error(name, f"no class '{class_name}' in module '{module_name}'")
        return cls

    def _validate(self, name: str, cls: type, configuration: dict) -> None:
        model = getattr(cls, "HOConfig", None)
        if model is None:
            return
        mode = ConfiguredObject.HOConfig.validation_mode
        ConfiguredObject.HOConfig.validation_mode = "lax"
        try:
            config = model(**configuration)
        except pydantic.ValidationError as ex:
            for msg in _format_errors(ex, prefix="configuration"):
                self.add_error(name, f"{msg}  [{cls.__name__}]")
            return
        except TypeError as ex:
            self.add_error(name, f"invalid configuration: {ex}")
            return
        finally:
            ConfiguredObject.HOConfig.validation_mode = mode

        undeclared = config.undeclared_properties()
        if undeclared:
            msg = (
                f"configuration: properties not declared in {cls.__name__}.HOConfig:"
                f" {', '.join(undeclared)}"
            )
            if self.strict:
                self.add_error(name, msg)
            else:
                self.add_warning(name, msg)


def _format_errors(ex: pydantic.ValidationError, prefix: str) -> list[str]:
    result = []
    for err in ex.errors():
        loc = ".".join(str(x) for x in (prefix, *err["loc"]))
        value = repr(err.get("input"))
        value = value if len(value) <= 60 else value[:57] + "..."
        result.append(f"{loc}: {err['msg']} (value: {value})")
    return result


def _xml_value(text: str | None) -> Any:
    """As BaseHardwareObjects.HardwareObjectNode._set_property"""
    value = str(text or "")
    if value == "None":
        return None
    for convert in (int, float):
        try:
            return convert(value)
        except ValueError:
            pass
    return {"True": True, "False": False}.get(value, value)


def xml_configuration(root: ET.Element) -> dict:
    """Configuration of an XML file, as built by _create_config_for_xml_hwobj"""

    def is_complex(el):
        return any(isinstance(k.tag, str) for k in el)

    def node(el):
        res, complex_ = {}, defaultdict(list)
        for k in el:
            if not isinstance(k.tag, str) or k.tag in ("command", "channel"):
                continue
            if k.get("href") or k.get("hwrid"):
                # referenced hardware object, in the node by role
                complex_[k.get("role") or k.tag].append({})
            elif is_complex(k) or k.tag == "object":
                complex_[k.tag].append(node(k))
            else:
                res[k.tag] = _xml_value(k.text)
        res.update(complex_)
        return res

    props, complex_ = {}, defaultdict(list)
    for k in root:
        if not isinstance(k.tag, str) or k.tag in ("command", "channel"):
            continue
        if k.get("href") or k.get("hwrid"):
            continue  # contained hardware object (by role)
        if is_complex(k) or k.tag == "object":
            complex_[k.tag].append(node(k))
        else:
            props[k.tag] = _xml_value(k.text)
    for tag, objs in complex_.items():
        props[tag] = objs[0] if len(objs) == 1 else objs
    return props


def check_configuration(
    lookup_path: str | list[str], strict: bool = False
) -> ConfigurationCheck:
    """Check the configuration files found in lookup_path (as given to
    init_hardware_repository: a list, or directories separated by os.pathsep)
    """
    if isinstance(lookup_path, str):
        lookup_path = lookup_path.split(os.path.pathsep)
    lookup_path = [os.path.abspath(os.path.expanduser(p)) for p in lookup_path if p]
    existing = [p for p in lookup_path if os.path.isdir(p)]
    check = ConfigurationCheck(existing or lookup_path, strict=strict)
    if not existing:
        check.add_error(
            ", ".join(lookup_path) or "-", "configuration directory not found"
        )
        return check
    return check.run()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check the MXCuBE hardware object configuration files"
    )
    parser.add_argument(
        "-r",
        "--repository",
        required=True,
        help=f"configuration directory, or directories separated by '{os.pathsep}'",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="report properties not declared in the HOConfig models as errors",
    )
    args = parser.parse_args(argv)
    check = check_configuration(args.repository, strict=args.strict)
    print(check.report())  # noqa: T201
    return 0 if check.ok else 1


if __name__ == "__main__":
    sys.exit(main())
