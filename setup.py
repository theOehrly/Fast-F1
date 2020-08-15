from setuptools import setup

info = {
    'name': 'fastf1',
    'version': 'v2.0.1',
    'author': 'Oehrly',
    'author_email': 'oehrly@mailbox.org',
    'packages': ['fastf1', 'fastf1.experimental'],
    'include_package_data': True,
    'install_requires': [
        'numpy', 'pandas', 'requests', 'requests_cache', 'matplotlib',
        'fuzzywuzzy', 'scipy'
    ],
    'license': 'MIT',
    'url': '',
    'description': 'Wrapper library for F1 data and telemetry with additional data processing capabilities.',
    'zip_safe': False
}

if __name__ == '__main__':
    import sys
    if sys.version_info < (3, 8):
        sys.exit('Sorry, Python < 3.8 is not supported,'
                 + ' please update to install.')
    else:
        setup(**info)
