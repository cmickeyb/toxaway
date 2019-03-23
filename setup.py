#!/usr/bin/env python
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# this should only be run with python3
import os
import sys
if sys.version_info[0] < 3:
    print('ERROR: must run with python3')
    sys.exit(1)

from setuptools import setup, find_packages

script_dir = os.path.dirname(os.path.realpath(__file__))
pdo_root_dir = os.path.abspath(os.path.join(script_dir, '..'))
install_root_dir = os.environ.get('PDO_HOME', '/opt/pdo')

def recursive_glob(src_root) :
    results = []
    for base, dirs, files in os.walk(src_root) :
        expanded_files = list(map(lambda file : os.path.join(base, file), files))
        results.append((os.path.join(install_root_dir, base), expanded_files))
    return results

data_files = []
data_files.extend(recursive_glob('etc'))
data_files.extend(recursive_glob('html'))
data_files.extend(recursive_glob('templates'))

setup(
    name='toxaway',
    version='0.1.1',
    packages=find_packages(),
    include_package_data=True,
    data_files=data_files,
    install_requires=[
        'flask',
    ],
    entry_points = {
        'console_scripts' : [ 'toxaway-server = toxaway.scripts.server:Main' ]
    }
)
