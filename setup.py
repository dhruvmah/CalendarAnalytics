from setuptools import setup

REQUIREMENTS = [i.strip() for i in open("requirements.txt").readlines()]

setup(
    name='NameAnalyzer',
    packages=['NameAnalyzer'],
    include_package_data=True,
    install_requires=REQUIREMENTS
)

