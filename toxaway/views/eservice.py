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
from wtforms import RadioField, StringField, SubmitField
from wtforms.validators import DataRequired, URL

from toxaway.models.profile import Profile
from toxaway.models.eservice import EnclaveService, EnclaveServiceList

import logging
logger = logging.getLogger(__name__)

__all__ = [ 'register' ]

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
            choices.append((eservice.file_name, eservice.enclave_service_url))

        form.eservice_list.choices = choices

        if form.validate_on_submit() :
            eservice = EnclaveService.load(self.config, form.eservice_list.data, use_raw=True)
            if eservice is None :
                logger.info('no such eservice as <%s>', form.eservice_list.data)
                flash('failed to find the eservice')
                render_template('error.html', title='An Error Occurred', profile=profile)

            return render_template('eservice/view.html', title='View EService', eservice=eservice, profile=profile)
        else :
            logger.debug('ERRORS: %s', form.errors)
            return render_template('eservice/pick.html', title='Pick EService', form=form, profile=profile)

## ----------------------------------------------------------------
## ----------------------------------------------------------------
class __Add_Enclave_Service_Form__(FlaskForm) :
    eservice_url = StringField('Service URL', validators=[URL(require_tld=False, message='must provide a URL')])
    eservice_name = StringField('Service Name', validators=[DataRequired(message='must provide a short name')])
    submit = SubmitField('Submit')

## ----------------------------------------------------------------
## ----------------------------------------------------------------
class add_eservice_app(object) :
    def __init__(self, config) :
        self.__name__ = type(self).__name__
        self.config = config

    def __call__(self, *args) :
        logger.info('add eservice')

        # any update to the data store must be in the context of an authorized profile
        profile = Profile.load(self.config, session['profile_name'], session['profile_secret'])
        if profile is None :
            logger.info('missing required profile')
            return redirect(url_for('login_app'))

        form = __Add_Enclave_Service_Form__()

        if form.validate_on_submit() :
            logger.info('add enclave submit')

            logger.info('create enclave information')
            eservice = EnclaveService.create(self.config, form.eservice_url.data, name=form.eservice_name.data)
            if eservice is None :
                logger.info('no eservice found')
                flash('failed to find the eservice')
                return render_template('error.html', title='An Error Occurred', profile=profile)

            return render_template('eservice/view.html', title='View Enclave Service', eservice=eservice, profile=profile)

        else :
            logger.info('re-render; %s', form.errors)
            return render_template('eservice/add.html', title='Add Enclave Service', form=form, profile=profile)

## ----------------------------------------------------------------
## ----------------------------------------------------------------
class view_eservice_app(object) :
    def __init__(self, config) :
        self.__name__ = type(self).__name__
        self.config = config

    def __call__(self, eservice_id, *args) :
        logger.info('view eservice')

        # any update to the data store must be in the context of an authorized profile
        profile = Profile.load(self.config, session['profile_name'], session['profile_secret'])
        if profile is None :
            logger.info('missing required profile')
            return redirect(url_for('login_app'))

        eservice = EnclaveService.load(self.config, eservice_id, use_raw=False)
        if eservice is None :
            logger.info('no such eservice as <%s>', eservice_id)
            flash('failed to find the eservice')
            render_template('error.html', title='An Error Occurred', profile=profile)

        return render_template('eservice/view.html', title='View EService', eservice=eservice, profile=profile)

## ----------------------------------------------------------------
## ----------------------------------------------------------------
def register(app, config) :
    logging.info('register auth apps')
    app.add_url_rule('/eservice/pick', None, pick_eservice_app(config), methods=['GET', 'POST'])
    app.add_url_rule('/eservice/add', None, add_eservice_app(config), methods=['GET', 'POST'])
    app.add_url_rule('/eservice/view/<eservice_id>', None, view_eservice_app(config), methods=['GET'])
