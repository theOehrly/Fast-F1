import pytest
import subprocess

pytestmark = pytest.mark.prjdoc


def test_readme_renders():
    # verify that the readme file renders without errors for pypi too
    ret = subprocess.call('python -m readme_renderer README.rst', shell=True,
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL)

    if ret != 0:
        raise Exception("README fails to render correctly!")
