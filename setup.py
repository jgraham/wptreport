# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import glob
import os
import sys
import textwrap

from setuptools import setup, find_packages

here = os.path.split(__file__)[0]

PACKAGE_NAME = 'wptreport'
PACKAGE_VERSION = '0.1'

# Dependencies
with open(os.path.join(here, "requirements.txt")) as f:
    deps = f.read().splitlines()

profile_dest = None
dest_exists = False

setup(name=PACKAGE_NAME,
      version=PACKAGE_VERSION,
      description="Tool for generating reports from wptrunner output",
      author='Mozilla Automation and Testing Team',
      author_email='tools@lists.mozilla.org',
      license='MPL 2.0',
      packages=find_packages(),
      entry_points={
          'console_scripts': [
              'wptreport-db = wptreport.dbhandler:main',
          ]
      },
      platforms=['Any'],
      classifiers=['Development Status :: 4 - Beta',
                   'Environment :: Console',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
                   'Operating System :: OS Independent'],
      package_data={},
      include_package_data=True,
      install_requires=deps
     )
