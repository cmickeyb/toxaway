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

from flask import redirect, render_template, session, url_for, flash

from flask_wtf import FlaskForm
from wtforms import RadioField, SubmitField
from wtforms.validators import DataRequired, URL

from toxaway.models.profile import Profile
from toxaway.models.eservice import EnclaveService, EnclaveServiceList

import logging
logger = logging.getLogger(__name__)

## ----------------------------------------------------------------
## ----------------------------------------------------------------
class __Pick_Enclave_Service_Form__(FlaskForm) :
    eservice_list = RadioField('Enclave Service URL', choices=[])
    submit = SubmitField('Submit')

## ----------------------------------------------------------------
## ----------------------------------------------------------------
class pick_eservice_app(object) :
    def __init__(self, config) :
        self.__name__ = type(self).__name__
        self.config = config

    def __call__(self, *args) :
        # any update to the data store must be in the context of an authorized profile
        profile = Profile.load(self.config, session['profile_name'], session['profile_secret'])
        if profile is None :
            logger.info('missing required profile')
            return redirect(url_for('login_app'))

        eservice_list = EnclaveServiceList.load(self.config)
        if eservice_list.count == 0 :
            return redirect(url_for('add_eservice_app'))

        form = __Pick_Enclave_Service_Form__()

        choices = []
        for eservice in eservice_list :
            choices.append((eservice.eservice_id, eservice.name))

        form.eservice_list.choices = choices

        if form.validate_on_submit() :
            return redirect(url_for('view_eservice_app', eservice_id=form.eservice_list.data))
        else :
            logger.debug('ERRORS: %s', form.errors)
            return render_template('eservice/pick.html', title='Pick EService', form=form, profile=profile)
