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
from toxaway.models.contract import Contract
from toxaway.models.eservice import EnclaveService, EnclaveServiceList
from toxaway.models.pservice import ProvisioningService, ProvisioningServiceList

import logging
logger = logging.getLogger(__name__)

## ----------------------------------------------------------------
## ----------------------------------------------------------------
class __Set_Preferences_Form__(FlaskForm) :
    invoke_list = RadioField('Preferred EService for Invocation', choices=[])
    update_list = RadioField('Preferred EService for Updates', choices=[])
    contract_name = StringField('Contract Object Name')
    submit = SubmitField('Submit')

## ----------------------------------------------------------------
## ----------------------------------------------------------------
class set_preferences_app(object) :
    def __init__(self, config) :
        self.__name__ = type(self).__name__
        self.config = config

    def __call__(self, contract_id, *args) :
        logger.info('set contract preferences')
        logger.info("selected contract id is %s", contract_id)

        # any update to the data store must be in the context of an authorized profile
        profile = Profile.load(self.config, session['profile_name'], session['profile_secret'])
        if profile is None :
            logger.info('missing required profile')
            return redirect(url_for('login_app'))

        contract = Contract.load(self.config, contract_id, use_raw=False)
        if contract is None :
            logger.info('no such contract')
            flash('failed to find contract')
            return render_template('error.html', title='An Error Occurred', profile=profile)

        form = __Set_Preferences_Form__()

        eservice_list = EnclaveServiceList.load(self.config)

        form.invoke_list.choices = [('random', 'random')]
        for enclave_id in contract.provisioned_enclaves :
            eservice = eservice_list.get_by_enclave_id(enclave_id)
            form.invoke_list.choices.append((eservice.eservice_id, eservice.name))

        form.update_list.choices = [('random', 'random')]
        for enclave_id in contract.provisioned_enclaves :
            eservice = eservice_list.get_by_enclave_id(enclave_id)
            form.update_list.choices.append((eservice.eservice_id, eservice.name))

        if form.validate_on_submit() :
            logger.info('invoke: %s', form.invoke_list.data)

            invoke_eservice = EnclaveService.load(self.config, form.invoke_list.data)
            logger.info('invoke enclave id: %s', invoke_eservice.enclave_id)

            update_eservice = EnclaveService.load(self.config, form.update_list.data)
            logger.info('update enclave id: %s', invoke_eservice.enclave_id)

            contract.invoke_enclave = invoke_eservice.enclave_id
            contract.update_enclave = update_eservice.enclave_id
            if form.contract_name.data :
                contract.name = form.contract_name.data
            contract.save(self.config)

            return redirect(url_for('contract_view_app', contract_id=contract_id))

        else :
            logger.info('incoming data for set preferences: %s', form.invoke_list.data)

            form.contract_name.data = contract.name
            form.invoke_list.default = contract.invoke_enclave
            form.update_list.default = contract.update_enclave

            logger.info('re-render; %s', form.errors)
            return render_template('contract/preferences.html', title='Set Contract Preferences',
                                   contract=contract, form=form, profile=profile)
