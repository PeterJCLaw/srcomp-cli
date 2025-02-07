from setuptools import find_namespace_packages, setup

with open('README.rst') as f:
    long_description = f.read()

setup(
    name='sr.comp.cli',
    version='1.11.0',
    project_urls={
        'Documentation': 'https://srcomp-cli.readthedocs.org/',
        'Code': 'https://github.com/PeterJCLaw/srcomp-cli',
        'Issue tracker': 'https://github.com/PeterJCLaw/srcomp-cli/issues',
    },
    packages=find_namespace_packages(include=['sr.*']),
    namespace_packages=['sr', 'sr.comp'],
    description=(
        "Command line tools for interacting with the state of the Student "
        "Robotics Competition"
    ),
    long_description=long_description,
    author="Student Robotics Competition Software SIG",
    author_email='srobo-devel@googlegroups.com',
    install_requires=[
        'python-dateutil >=2.2, <3',
        'Fabric >= 2.7, <4',
        'invoke >= 1.7, <3',
        'sr.comp >=1.8, <2',
        'reportlab >=3.1.44, <5',
        'requests >=2.5.1, <3',
        # Work around https://sourceforge.net/p/ruamel-yaml/tickets/534/, where
        # number-zero (0) keys don't round trip under YAML 1.1, by avoiding
        # 0.18.x versions containing the bug.
        'ruamel.yaml >=0.15, !=0.18.7, !=0.18.8, <1.0',
        'mido >=1.1, <2',
        'tabulate >=0.8.9, <0.10',
    ],
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'srcomp = sr.comp.cli.command_line:main',
        ],
    },
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Utilities',
    ],
)
