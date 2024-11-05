# setup.py
import os
from setuptools import setup
from setuptools.command.install import install

class PostInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        install.run(self)
        os.system('python post_install.py')

setup(
    name='scramble',
    version='0.1.0',
    packages=['src/scramble'],
    install_requires=[
        'rich',
        'anthropic>=0.18.0',
        'click',
        'sentence-transformers',
        'click>=8.0.0',
        'numpy>=1.20.0',
        'sentence-transformers>=2.0.0',
        'nltk'
    ],
    cmdclass={
        'install': PostInstallCommand,
    },
)
