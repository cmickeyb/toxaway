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

from toxaway.views.pservice.add_app import add_pservice_app
from toxaway.views.pservice.pick_app import pick_pservice_app
from toxaway.views.pservice.view_app import view_pservice_app

import logging
logger = logging.getLogger(__name__)

__all__ = [ 'register' ]

## ----------------------------------------------------------------
## ----------------------------------------------------------------
def register(app, config) :
    logging.info('register pservice apps')
    app.add_url_rule('/pservice/pick', None, pick_pservice_app(config), methods=['GET', 'POST'])
    app.add_url_rule('/pservice/add', None, add_pservice_app(config), methods=['GET', 'POST'])
    app.add_url_rule('/pservice/view/<pservice_id>', None, view_pservice_app(config), methods=['GET'])
