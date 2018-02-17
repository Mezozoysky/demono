#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from setuptools import setup, find_packages

top_dir = os.path.abspath(os.path.dirname(__file__))
package_name = 'demono'
package_desc = 'Simple Unix daemon library'
package_version = None
with open(os.path.join(top_dir, package_name, '__version__.py')) as f:
    tmp = {}
    exec(f.read(), tmp)
    package_version = tmp['__version__']
    del tmp
package_requires = open("requires.list").read().split('\n')
readme_content = open("README.md").read()

setup(
    name=package_name,
    version=package_version,
    description=package_desc,
    long_description=readme_content,
    author='Stanislav Demyanovich',
    author_email='mezozoysky@gmail.com',
    license='MIT',
    keywords="automation development c++",
    url='http://mezozoysky.ru/da',
    packages=find_packages(exclude=('tests')),
    include_package_data=True,
    install_requires=package_requires,
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.6',
    ],
)
