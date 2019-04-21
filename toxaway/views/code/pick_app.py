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
from toxaway.models.contract_code import ContractCode, ContractCodeList

import logging
logger = logging.getLogger(__name__)

## ----------------------------------------------------------------
## ----------------------------------------------------------------
class __Pick_Contract_Code_Form__(FlaskForm) :
    contract_code_list = RadioField('Contract Code Name', choices=[])
    submit = SubmitField('Submit')

## ----------------------------------------------------------------
## ----------------------------------------------------------------
class pick_contract_code_app(object) :
    def __init__(self, config) :
        self.__name__ = type(self).__name__
        self.config = config

    def __call__(self, *args) :
        # any update to the data store must be in the context of an authorized profile
        profile = Profile.load(self.config, session['profile_name'], session['profile_secret'])
        if profile is None :
            logger.info('missing required profile')
            return redirect(url_for('login_app'))

        code_list = ContractCodeList.load(self.config)
        if code_list.count == 0 :
            return redirect(url_for('add_contract_code_app'))

        form = __Pick_Contract_Code_Form__()

        choices = []
        for ccode in code_list :
            choices.append((ccode.code_hash, ccode.name))

        form.contract_code_list.choices = choices

        if form.validate_on_submit() :
            contract_code = ContractCode.load(self.config, form.contract_code_list.data, use_raw=False)
            if contract_code is None :
                logger.info('no such contract code')
                flash('failed to find contract code')
                return render_template('error.html', title='An Error Occurred', profile=profile)

            return render_template('contract_code/view.html',
                                   title='View Contract Code',
                                   contract_code=contract_code,
                                   profile=profile)
        else :
            logger.debug('ERRORS: %s', form.errors)
            return render_template('contract_code/pick.html', title='Pick Contract Code', form=form, profile=profile)
