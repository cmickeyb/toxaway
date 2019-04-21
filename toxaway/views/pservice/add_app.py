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
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL

from toxaway.models.profile import Profile
from toxaway.models.pservice import ProvisioningService

import logging
logger = logging.getLogger(__name__)

## ----------------------------------------------------------------
## ----------------------------------------------------------------
class __Add_Provisioning_Service_Form__(FlaskForm) :
    pservice_url = StringField('Provisioning Service URL', validators=[URL(require_tld=False, message='must provide a URL')])
    pservice_name = StringField('Provisioning Service Name', validators=[DataRequired(message='must provide a short name')])
    submit = SubmitField('Submit')

## ----------------------------------------------------------------
## ----------------------------------------------------------------
class add_pservice_app(object) :
    def __init__(self, config) :
        self.__name__ = type(self).__name__
        self.config = config

    def __call__(self, *args) :
        logger.info('add pservice')

        # any update to the data store must be in the context of an authorized profile
        profile = Profile.load(self.config, session['profile_name'], session['profile_secret'])
        if profile is None :
            logger.info('missing required profile')
            return redirect(url_for('login_app'))

        form = __Add_Provisioning_Service_Form__()

        if form.validate_on_submit() :
            logger.info('add enclave submit')

            logger.info('create enclave information')
            pservice = ProvisioningService.create(self.config, form.pservice_url.data, name=form.pservice_name.data)
            if pservice is None :
                logger.info('no pservice found')
                flash('failed to find the pservice')
                return render_template('error.html', title='An Error Occurred', profile=profile)

            return render_template('pservice/view.html', title='View Provisioning Service', pservice=pservice, profile=profile)

        else :
            logger.info('re-render; %s', form.errors)
            return render_template('pservice/add.html', title='Add Provisioning Service', form=form, profile=profile)
