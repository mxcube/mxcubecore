"""Tests for the ConfiguredObject.HOConfig configuration model"""

import pydantic
import pytest

from mxcubecore.BaseHardwareObjects import ConfiguredObject


class DeclaredConfig(ConfiguredObject.HOConfig):
    run_number: int = 1
    methods: list = []


@pytest.fixture
def validation_mode():
    """Restore the validation mode after each test"""
    yield ConfiguredObject.HOConfig.set_validation_mode
    ConfiguredObject.HOConfig.set_validation_mode("lax")


def test_undeclared_model_accepts_anything(validation_mode):
    validation_mode("strict")
    config = ConfiguredObject.HOConfig(foo=1, bar="x")
    assert config.foo == 1
    assert config.model_dump() == {"foo": 1, "bar": "x"}
    assert config.undeclared_properties() == []


def test_declared_fields_are_validated_and_dumped():
    config = DeclaredConfig(run_number="5")
    assert config.run_number == 5
    assert config.model_dump() == {"run_number": 5, "methods": []}
    assert DeclaredConfig().methods is not DeclaredConfig().methods


def test_lax_mode_accepts_undeclared(validation_mode):
    validation_mode("lax")
    config = DeclaredConfig(zeta=1, alpha=2)
    assert config.zeta == 1
    assert config.undeclared_properties() == ["alpha", "zeta"]


def test_strict_mode_rejects_undeclared(validation_mode):
    validation_mode("strict")
    with pytest.raises(pydantic.ValidationError, match="alpha"):
        DeclaredConfig(alpha=2)
    assert DeclaredConfig(run_number=3).run_number == 3


def test_invalid_validation_mode():
    with pytest.raises(ValueError, match="validation mode"):
        ConfiguredObject.HOConfig.set_validation_mode("medium")