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

import random

import pdo.service_client.service_data.eservice as eservice_db
from pdo.client.SchemeExpression import SchemeExpression
from toxaway.models.eservice import EnclaveService

import logging
logger = logging.getLogger(__name__)

__all__ = ['ContractResponse', 'InvocationException']

# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
class InvocationException(Exception) :
    pass

# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
class ContractResponse(object) :

    ## ----------------------------------------------------------------
    @classmethod
    def invoke_method(cls, config, profile, contract, expression) :
        logger.info('load enclave service from %s', contract.update_enclave)
        update_enclave = contract.update_enclave
        if update_enclave == 'random' :
            update_enclave = random.choice(contract.provisioned_enclaves)

        eservice = eservice_db.get_client_by_id(update_enclave)
        ## eservice = EnclaveService.load(config, update_enclave).eservice_client
        update_request = contract.create_update_request(profile.keys, expression, eservice)
        update_response = update_request.evaluate()

        if update_response.status is False :
            raise InvocationException(update_response.response)

        if update_response.state_changed :
            logger.info('update the contract state')
            try :
                contract_config = config['ContentPaths']
                state_directory = contract_config['State']
            except KeyError :
                raise Exception('missing contract data configuration')

            contract.contract_state.save_to_cache(data_dir = state_directory)
            contract.set_state(update_response.raw_state)

            logger.info('submit the transaction')
            try :
                ledger_config = config['Sawtooth']
            except KeyError :
                raise Exception('missing ledger configuration')

            update_response.commit_asynchronously(ledger_config)

        # first try to parse the result as a Scheme expression, if that
        # fails, then just treat it as a string and return it; we know
        # that the eservice thinks this was a good response
        try :
            expr = SchemeExpression.ParseExpression(update_response.result)
        except Exception as e :
            expr = SchemeExpression.make_string(update_response.result)

        return cls(expr)

    ## ----------------------------------------------------------------
    def __init__(self, result) :
        self.__result__ = result

    ## ----------------------------------------------------------------
    def __getattr__(self, attr) :
        if hasattr(self.__result__, attr) :
            return self.__result__.__getattribute__(attr)

        raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, attr))
