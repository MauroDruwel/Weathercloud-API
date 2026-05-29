from __future__ import annotations

import weathercloud


def test_public_api_exports():
    expected = {
        "WeathercloudClient",
        "WeathercloudError",
        "VariableCode",
        "CurrentConditions",
        "StationInfo",
        "__version__",
    }
    assert expected.issubset(set(weathercloud.__all__))
    for name in expected:
        assert hasattr(weathercloud, name)


def test_version_is_string():
    assert isinstance(weathercloud.__version__, str)
    assert weathercloud.__version__.count(".") >= 2
