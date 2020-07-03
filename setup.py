from distutils.core import setup

info = {
    'name': 'fastf1',
    'version': 'v2.0.1',
    'author': 'Oehrly',
    'author_email': 'oehrly@mailbox.org',
    'packages': ['fastf1', 'fastf1.experimental'],
    'install_requires': [
        'numpy', 'pandas', 'requests', 'requests_cache', 'matplotlib',
        'python-Levenshtein', 'fuzzywuzzy', 'scipy'
    ],
    'license': 'MIT',
    'url': '',
    'descritpion': 'Wrapper library for F1 data and telemetry with additional data processing capabilities.',
    'zip_safe': False
}

if __name__ == '__main__':
    import sys
    if sys.version_info < (3, 8):
        sys.exit('Sorry, Python < 3.8 is not supported,'
                 + ' please update to install.')
    else:
        setup(**info)
