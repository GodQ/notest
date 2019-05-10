import sys
import setuptools
import re

install_requires = list()
dependency_links = list()
uninstalled_pkgs = list()
with open("requirements.txt", "r", encoding='utf-8') as f:
    for line in f:
        if re.match("^[\w_-]*(==(\d+\.)*\d+){0,1}$", line.strip()):
            install_requires.append(line.strip())
        elif line.strip() and not line.strip().startswith("#"):
            uninstalled_pkgs.append(line.strip())

for i, pkg in enumerate(uninstalled_pkgs):
    if pkg.startswith("-e "):
        dependency_links.append(pkg.lstrip("-e").strip())
        del uninstalled_pkgs[i]

setuptools.setup(name='notest',
      version='0.0.3',
      description='Not Only Test! One Excellent Python Testing Tool',
      long_description='Not Only Test! One Excellent Python Testing Tool.',
      author='Chuanhao Qu',
      author_email='quchuanhao@gmail.com',
      url='https://github.com/godq/pyresttest',
      keywords=['rest', 'web', 'http', 'testing', "notest", "api"],
      classifiers=[
          'Environment :: Console',
          'License :: OSI Approved :: Apache Software License',
          'Natural Language :: English',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Topic :: Software Development :: Testing',
          'Topic :: Software Development :: Quality Assurance',
          'Topic :: Utilities'
      ],
      packages=setuptools.find_packages(where='.', exclude=(), include=('notest*')),
      license='Apache License, Version 2.0',
      install_requires=install_requires,
      dependency_links=dependency_links,
      include_package_data=True,
      zip_safe=False,
      entry_points={
        'console_scripts': [
            'notest = notest.main:command_line_run',
        ],
      },
)
