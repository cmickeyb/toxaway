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
from wtforms import RadioField, SelectMultipleField, StringField, SubmitField
from wtforms.validators import DataRequired, URL

from toxaway.models.profile import Profile
from toxaway.models.contract import Contract
from toxaway.models.contract_code import ContractCodeList, ContractCode
from toxaway.models.eservice import EnclaveService, EnclaveServiceList
from toxaway.models.pservice import ProvisioningService, ProvisioningServiceList
from toxaway.contract.create import Create

import logging
logger = logging.getLogger(__name__)

## ----------------------------------------------------------------
## ----------------------------------------------------------------
class __Create_Contract_Form__(FlaskForm) :
    eservice_list = SelectMultipleField('Pick Enclave Services')
    pservice_list = SelectMultipleField('Pick Provisioning Services')
    contract_code_list = RadioField('Contract Code')
    contract_name = StringField('Contract Object Name', validators=[DataRequired(message='must provide a short name')])
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

        # contract code
        code_list = ContractCodeList.load(self.config)
        if code_list.count == 0 :
            return redirect(url_for('add_contract_code_app'))

        form.contract_code_list.choices = []
        for ccode in code_list :
            form.contract_code_list.choices.append((ccode.code_hash, ccode.name))

        # eservice choices
        eservice_list = EnclaveServiceList.load(self.config)
        if eservice_list.count == 0 :
            return redirect(url_for('add_eservice_app'))

        form.eservice_list.choices = []
        for eservice in eservice_list :
            form.eservice_list.choices.append((eservice.eservice_id, eservice.name))

        # pservice choices
        pservice_list = ProvisioningServiceList.load(self.config)
        if pservice_list.count == 0 :
            return redirect(url_for('add_pservice_app'))

        form.pservice_list.choices = []
        for pservice in pservice_list :
            form.pservice_list.choices.append((pservice.file_name, pservice.name))

        # and now we work to process it
        if form.validate_on_submit() :
            logger.info("eservice list: %s", form.eservice_list.data)
            logger.info("pservice list: %s", form.pservice_list.data)
            logger.info("contract code: %s", form.contract_code_list.data)

            pservices = ProvisioningServiceList(self.config)
            for pservice_id in form.pservice_list.data :
                pservice_object = ProvisioningService.load(self.config, pservice_id, use_raw=False)
                if pservice_object is None :
                    logger.info('no such pservice as <%s>', pservice_id)
                    flash('failed to find the pservice: {0}'.format(pservice_id))
                    return render_template('error.html', title='An Error Occurred', profile=profile)
                pservices.add(pservice_object)

            eservices = EnclaveServiceList(self.config)
            for eservice_id in form.eservice_list.data :
                eservice_object = EnclaveService.load(self.config, eservice_id)
                if eservice_object is None :
                    logger.info('no such eservice as <%s>', eservice_id)
                    flash('failed to find the eservice: {0}'.format(eservice_id))
                    return render_template('error.html', title='An Error Occurred', profile=profile)
                eservices.add(eservice_object)

            contract_code = ContractCode.load(self.config, form.contract_code_list.data, use_raw=False)
            if contract_code is None :
                logger.info('no such contract code')
                flash('failed to find contract code')
                return render_template('error.html', title='An Error Occurred', profile=profile)

            contract_object = Create(self.config, profile, form.contract_name.data, contract_code, eservices, pservices)
            if contract_object is None :
                logger.info('failed to create the contract')
                flash('failed to create the contract')
                return render_template('error.html', title='An Error Occurred', profile=profile)

            return redirect(url_for('contract_view_app', contract_id=contract_object.safe_contract_id))

        else :
            logger.info('re-render; %s', form.errors)
            return render_template('contract/create.html', title='Create Contract', form=form, profile=profile)
