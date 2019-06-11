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
from toxaway.models.contract import Contract
from toxaway.models.eservice import EnclaveService
from toxaway.models.response import ContractResponse, InvocationException

import logging
logger = logging.getLogger(__name__)

__all__ = ['contract_invoke_app']

## ----------------------------------------------------------------
## ----------------------------------------------------------------
class __Contract_Invoke_Form__(FlaskForm) :
    expression = StringField('Expression')
    submit = SubmitField('Submit')

## ----------------------------------------------------------------
## ----------------------------------------------------------------
class contract_invoke_app(object) :
    def __init__(self, config) :
        self.__name__ = type(self).__name__
        self.config = config

    def __call__(self, contract_id, *args) :
        logger.info('contract_view_app')

        # any update to the data store must be in the context of an authorized profile
        profile = Profile.load(self.config, session['profile_name'], session['profile_secret'])
        if profile is None :
            logger.info('missing required profile')
            return redirect(url_for('login_app'))

        logger.info("selected contract id is %s", contract_id)
        contract = Contract.load(self.config, contract_id, use_raw=False)
        if contract is None :
            logger.info('no such contract')
            flash('failed to find contract')
            return render_template('error.html', title='An Error Occurred', profile=profile)

        form = __Contract_Invoke_Form__()

        if form.validate_on_submit() :
            try :
                expression = form.expression.data
                response = ContractResponse.invoke_method(self.config, profile, contract, expression)
            except InvocationException as e :
                logger.info('invocation failed: %s', str(e))
                return render_template('contract/invoke.html', title='Invocation Results',
                                       contract=contract, form=form, profile=profile, result=None, error=str(e))

            logger.info('invoke: %s', form.invoke_list.data)
            return render_template('contract/invoke.html', title='Invocation Results',
                                   contract=contract, form=form, profile=profile, result=result, error=None)
        else :
            logger.info('re-render; %s', form.errors)
            return render_template('contract/invoke.html', title='Invoke Contract Method',
                                   contract=contract, form=form, profile=profile, result=None, error=None)
