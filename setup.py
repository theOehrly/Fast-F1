from setuptools import setup


if __name__ == '__main__':
    import sys
    if sys.version_info < (3, 8):
        sys.exit('Sorry, Python < 3.8 is not supported,'
                 + ' please update to install.')
    else:
        setup()
