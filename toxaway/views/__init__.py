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

from flask import Flask

import toxaway.views.contract
import toxaway.views.code
import toxaway.views.eservice
import toxaway.views.index
import toxaway.views.login
import toxaway.views.pservice

def register(config) :
    try :
        template_folder = config['ContentPaths']['Template']
    except KeyError as ke :
        logger.error('missing configuration for template folder')
        raise Exception('initialization failed')

    app = Flask(__name__, template_folder=template_folder)
    app.config['SECRET_KEY'] = 'four score and seven years ago'
    #app.secret_key = 'four score and seven years ago'

    toxaway.views.contract.register(app, config)
    toxaway.views.code.register(app, config)
    toxaway.views.eservice.register(app, config)
    toxaway.views.index.register(app, config)
    toxaway.views.login.register(app, config)
    toxaway.views.pservice.register(app, config)

    return app
