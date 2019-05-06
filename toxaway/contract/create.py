#!/usr/bin/env python

# Copyright 2018 Intel Corporation
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

import os, sys
import logging
import argparse
import random
import tempfile
import time

import pdo.common.config as pconfig
import pdo.common.logger as plogger
import pdo.common.crypto as pcrypto
import pdo.common.utility as putils

from pdo.common.keys import ServiceKeys
from pdo.contract import ContractCode
from pdo.contract import ContractState
from pdo.contract import Contract
from pdo.contract import register_contract
from pdo.contract import add_enclave_to_contract
from pdo.service_client.enclave import EnclaveServiceClient
from pdo.service_client.provisioning import ProvisioningServiceClient

import toxaway.models.contract

logger = logging.getLogger(__name__)

## -----------------------------------------------------------------
def AddEnclaveSecrets(ledger_config, contract_id, client_keys, enclaveclients, provclients) :
    secrets = {}
    encrypted_state_encryption_keys = {}
    for enclaveclient in enclaveclients:
        psecrets = []
        for provclient in provclients:
            # Get a pspk:esecret pair from the provisioning service for each enclave
            sig_payload = pcrypto.string_to_byte_array(enclaveclient.enclave_id + contract_id)
            secretinfo = provclient.get_secret(enclaveclient.enclave_id,
                                               contract_id,
                                               client_keys.verifying_key,
                                               client_keys.sign(sig_payload))
            logger.debug("pservice secretinfo: %s", secretinfo)

            # Add this pspk:esecret pair to the list
            psecrets.append(secretinfo)

        # Print all of the secret pairs generated for this particular enclave
        logger.debug('psecrets for enclave %s : %s', enclaveclient.enclave_id, psecrets)

        # Verify those secrets with the enclave
        esresponse = enclaveclient.verify_secrets(contract_id, client_keys.verifying_key, psecrets)
        logger.debug("verify_secrets response: %s", esresponse)

        # Store the ESEK mapping in a dictionary key'd by the enclave's public key (ID)
        encrypted_state_encryption_keys[enclaveclient.enclave_id] = esresponse['encrypted_state_encryption_key']

        # Add this spefiic enclave to the contract
        add_enclave_to_contract(ledger_config,
                                client_keys,
                                contract_id,
                                enclaveclient.enclave_id,
                                psecrets,
                                esresponse['encrypted_state_encryption_key'],
                                esresponse['signature'])

    return encrypted_state_encryption_keys

## -----------------------------------------------------------------
def CreateContract(ledger_config, client_keys, enclaveclients, contract) :
    # Choose one enclave at random to use to create the contract
    enclaveclient = random.choice(enclaveclients)

    logger.info('Requesting that the enclave initialize the contract...')
    initialize_request = contract.create_initialize_request(client_keys, enclaveclient)
    initialize_response = initialize_request.evaluate()
    contract.set_state(initialize_response.raw_state)

    logger.info('Contract state created successfully')

    logger.info('Saving the initial contract state in the ledger...')

    cclinit_result = initialize_response.submit_initialize_transaction(ledger_config, wait=60)
    logger.info('contract initialized; %s', cclinit_result)

## -----------------------------------------------------------------
## -----------------------------------------------------------------
def Create(config, client_profile, contract_name, contract_code, eservices, pservices) :
    """
    client_profile -- toxaway.models.profile.Profile
    contract_code -- toxaway.models.contract_code.ContractCode
    eservices -- toxaway.models.eservice.EnclaveServiceList
    pservices -- toxaway.models.pservice.ProvisioningServiceList
    """

    ledger_config = config['Sawtooth']
    contract_config = config['ContentPaths']
    state_directory = contract_config['State']

    client_keys = client_profile.keys
    provisioning_service_keys = list(pservices.identities())


    try :
        pdo_code_object = contract_code.create_pdo_contract()
    except Exception as e :
        logger.error('failed to create the contract object; %s', str(e))
        return None

    try :
        pdo_contract_id = register_contract(
            ledger_config, client_keys, pdo_code_object, provisioning_service_keys)

        logger.info('Registered contract %s with id %s', contract_code.name, pdo_contract_id)
        pdo_contract_state = ContractState.create_new_state(pdo_contract_id)
        contract = Contract(pdo_code_object, pdo_contract_state, pdo_contract_id, client_keys.identity)
    except Exception as e :
        logger.error('failed to register the contract; %s', str(e))
        return None

    logger.info('Contract created')

    enclaveclients = []
    for eservice in eservices :
        enclaveclients.append(eservice.eservice_client)

    provclients = []
    for pservice in pservices :
        provclients.append(pservice.pservice_client)

    encrypted_state_encryption_keys = AddEnclaveSecrets(
        ledger_config, pdo_contract_id, client_keys, enclaveclients, provclients)

    for enclave_id in encrypted_state_encryption_keys :
        encrypted_key = encrypted_state_encryption_keys[enclave_id]
        contract.set_state_encryption_key(enclave_id, encrypted_key)

    CreateContract(ledger_config, client_keys, enclaveclients, contract)

    contract.contract_state.save_to_cache(data_dir = state_directory)
    logger.info('state saved to cache')

    with tempfile.NamedTemporaryFile() as pdo_temp :
        contract.save_to_file(pdo_temp.name)
        toxaway_contract = toxaway.models.contract.Contract.import_contract(config, pdo_temp, contract_name)

    return toxaway_contract
