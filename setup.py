from setuptools import setup


if __name__ == '__main__':
    import sys
    import re
    if sys.version_info < (3, 8):
        sys.exit('Sorry, Python < 3.8 is not supported,'
                 + ' please update to install.')
    else:
        # load version number from file in sources dir without importing
        with open('fastf1/version.py') as vfobj:
            vstring = str(vfobj.read())
            version = re.search(r"(\d.\d.\d)", vstring)[0]
        setup(version=version)
