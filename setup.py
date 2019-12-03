from distutils.core import setup

setup(
        name='f1telemetry',
        version='v0.1.0',
        author='Ax_6',
        author_email='axolo6@gmail.com',
        packages=['f1telemetry'],
        install_requires=[
            'numpy', 'pandas', 'requests', 'requests_cache', 'matplotlib'
        ],
        license='MIT',
        url='',
        descritpion='Wrapper library for f1 data and telemetry',
        zip_safe=False
)
