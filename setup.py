from distutils.core import setup

info = {
    'name': 'fastf1',
    'version': 'v0.1.1',
    'author': 'Ax_6',
    'author_email': 'axolo6@gmail.com',
    'packages': ['fastf1'],
    'install_requires': [
        'numpy', 'pandas', 'requests', 'requests_cache', 'matplotlib'
    ],
    'license': 'MIT',
    'url': '',
    'descritpion': 'Wrapper library for F1 data and telemetry',
    'zip_safe': False
}

if __name__ == '__main__':
    setup(**info)
