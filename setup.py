#!/usr/bin/env python
''' Package cryptomate '''

from setuptools import setup, find_packages
import cryptomate

setup(
    name='cryptomate',
    version='%d.%d.%d' % cryptomate.__VERSION__,
    author='Julien Hartmann',
    url='https://github.com/solid-abstractions/cryptomate/',
    description='Automated trading engine',
    classifiers=[
        'Development Status :: 1 - Planning',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Office/Business :: Financial',
    ],
    packages=find_packages(exclude=('tests', 'tests.*')),
    entry_points={
        'console_scripts': [
            'cryptomate = cryptomate.run:main',
        ],
    },
    python_requires='>=3.5',
    install_requires=[
        'aiohttp>=3.4.0',
    ],
    tests_require=['pytest', 'pytest-asyncio'],
)
