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

PY_VERSION=${shell python3 --version | sed 's/Python \(3\.[0-9]\).*/\1/'}
MOD_VERSION=${shell ../bin/get_version}

EGG_FILE = dist/toxaway-0.1.1-py${PY_VERSION}.egg
PYTHON_SOURCE = $(shell cat MANIFEST)

all: $(EGG_FILE)

$(EGG_FILE) : $(PYTHON_SOURCE) setup.py
	python setup.py bdist_egg

install: $(EGG_FILE)
	easy_install $<

manifest :
	rm -f MANIFEST
	find toxaway -iname '*.py' > MANIFEST
	find html -type f >> MANIFEST
	find templates -type f >> MANIFEST

clean:
	python setup.py clean --all
	rm -rf dist toxaway.egg-info

.phony : all
.phony : clean
.phone : install
.phony : test
