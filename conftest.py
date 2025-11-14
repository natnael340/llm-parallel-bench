import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-perf", action="store_true", default=False, help="run performance tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "perf: mark test as performance test")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-perf"):
        # --run-perf given in cli: do not skip performance tests
        return
    skip_perf = pytest.mark.skip(reason="need --run-perf option to run")
    for item in items:
        if "perf" in item.keywords:
            item.add_marker(skip_perf)