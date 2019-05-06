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
from toxaway.models.contract import ContractList, Contract, LedgerContract

import logging
logger = logging.getLogger(__name__)

## ----------------------------------------------------------------
## ----------------------------------------------------------------
class __Pick_Contract_Form__(FlaskForm) :
    contract_list = RadioField('Contract Name', choices=[])
    submit = SubmitField('Submit')

## ----------------------------------------------------------------
## ----------------------------------------------------------------
class contract_pick_app(object) :
    def __init__(self, config) :
        self.__name__ = type(self).__name__
        self.config = config

    def __call__(self, *args) :
        logger.info('contract_pick_app')

        # any update to the data store must be in the context of an authorized profile
        profile = Profile.load(self.config, session['profile_name'], session['profile_secret'])
        if profile is None :
            logger.info('missing required profile')
            return redirect(url_for('login_app'))

        contract_list = ContractList.load(self.config)
        if contract_list.count == 0 :
            return redirect(url_for('contract_import_app'))

        form = __Pick_Contract_Form__()

        choices = []
        for contract in contract_list :
            choices.append((contract.safe_contract_id, contract.name))

        form.contract_list.choices = choices

        if form.validate_on_submit() :
            contract_id = form.contract_list.data
            return redirect(url_for('contract_view_app', contract_id=contract_id))
        else :
            logger.info('ERRORS: %s', form.errors)
            return render_template('contract/pick.html', title='Pick Contract', form=form, profile=profile)
