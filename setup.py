# -*- coding: utf-8 -*-
"""setup.py: setuptools control."""
from setuptools import setup
import versioneer

with open('README.md', 'rb') as f:
    long_descr = f.read().decode('utf-8')


setup(
    name='seiscat',
    packages=['seiscat', 'seiscat.scripts', 'seiscat.configobj'],
    include_package_data=True,
    entry_points={
        'console_scripts': ['seiscat = seiscat.scripts.seiscat:main']
        },
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description='Keep a local seismic catalog',
    long_description=long_descr,
    long_description_content_type='text/markdown',
    author='Claudio Satriano',
    author_email='satriano@ipgp.fr',
    url='https://github.com/SeismicSource/SeisCat',
    license='GNU General Public License v3 or later (GPLv3+)',
    platforms='OS Independent',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: '
            'GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Physics'],
    install_requires=['obspy>=1.1.0'],
    python_requires='>3.7'
    )
