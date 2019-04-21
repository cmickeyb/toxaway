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

from toxaway.views.eservice.add_app import add_eservice_app
from toxaway.views.eservice.pick_app import pick_eservice_app
from toxaway.views.eservice.view_app import view_eservice_app

import logging
logger = logging.getLogger(__name__)

__all__ = [ 'register' ]

## ----------------------------------------------------------------
## ----------------------------------------------------------------
def register(app, config) :
    logging.info('register auth apps')
    app.add_url_rule('/eservice/pick', None, pick_eservice_app(config), methods=['GET', 'POST'])
    app.add_url_rule('/eservice/add', None, add_eservice_app(config), methods=['GET', 'POST'])
    app.add_url_rule('/eservice/view/<eservice_id>', None, view_eservice_app(config), methods=['GET'])
