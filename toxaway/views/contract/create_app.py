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
from flask_wtf.file import FileField, FileRequired
from wtforms import RadioField, StringField, SubmitField
from wtforms.validators import DataRequired, URL

from toxaway.models.profile import Profile
from toxaway.models.contract import ContractList, Contract

import logging
logger = logging.getLogger(__name__)

## ----------------------------------------------------------------
## ----------------------------------------------------------------
class __Create_Contract_Form__(FlaskForm) :
    eservice_url = StringField('Service URL', validators=[URL(require_tld=False, message='must provide a URL')])
    eservice_name = StringField('Service Name', validators=[DataRequired(message='must provide a short name')])
    submit = SubmitField('Submit')

## ----------------------------------------------------------------
## ----------------------------------------------------------------
class contract_create_app(object) :
    def __init__(self, config) :
        self.__name__ = type(self).__name__
        self.config = config

    def __call__(self, *args) :
        logger.info('create contract')

        # any update to the data store must be in the context of an authorized profile
        profile = Profile.load(self.config, session['profile_name'], session['profile_secret'])
        if profile is None :
            logger.info('missing required profile')
            return redirect(url_for('login_app'))

        form = __Create_Contract_Form__()

        if form.validate_on_submit() :
            return render_template('/view.html', title='View Enclave Service', eservice=eservice, profile=profile)

        else :
            logger.info('re-render; %s', form.errors)
            return render_template('eservice/add.html', title='Add Enclave Service', form=form, profile=profile)
