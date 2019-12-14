from distutils.core import setup

info = {
    'name': 'fastf1',
    'version': 'v1.2.0',
    'author': 'Ax_6',
    'author_email': 'axolo6@gmail.com',
    'packages': ['fastf1'],
    'install_requires': [
        'numpy', 'pandas', 'requests', 'requests_cache', 'matplotlib',
        'python-Levenshtein', 'fuzzywuzzy'
    ],
    'license': 'MIT',
    'url': '',
    'descritpion': 'Wrapper library for F1 data and telemetry',
    'zip_safe': False
}

if __name__ == '__main__':
    import sys
    if sys.version_info < (3,8):
        sys.exit('Sorry, Python < 3.8 is not supported,'
                 + ' please update to install.')
    else:
        setup(**info)
