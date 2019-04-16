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

from toxaway.views.contract.create_app import contract_create_app
from toxaway.views.contract.import_app import contract_import_app
from toxaway.views.contract.pick_app import contract_pick_app

import logging
logger = logging.getLogger(__name__)

__all__ = [ 'register' ]

## ----------------------------------------------------------------
## ----------------------------------------------------------------
def register(app, config) :
    logging.info('register contract creation')
    app.add_url_rule('/contract/create', None, contract_create_app(config), methods=['GET', 'POST'])
    app.add_url_rule('/contract/pick', None, contract_pick_app(config), methods=['GET', 'POST'])
    app.add_url_rule('/contract/import', None, contract_import_app(config), methods=['GET', 'POST'])
