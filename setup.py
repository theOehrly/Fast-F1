from distutils.core import setup
from f1telemetry import __version__

setup(
        name='f1telemetry',
        version=__version__,
        author='Ax_6',
        author_email='axolo6@gmail.com',
        packages=['f1telemetry'],
        install_requires=[
            'numpy', 'pandas', 'zlib', 'requests', 'requests_cache', 
            'matplotlib'
        ],
        license='MIT',
        url='',
        descritpion='Wrapper library for f1 data and telemetry',
        zip_safe=False
)
