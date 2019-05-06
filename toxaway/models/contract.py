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

import base64
import glob
import hashlib
import json
import os

from pdo.contract.state import ContractState as pdo_contract_state
from pdo.contract.code import ContractCode as pdo_contract_code
from pdo.contract.contract import Contract as pdo_contract
from sawtooth.helpers import pdo_connect

import logging
logger = logging.getLogger(__name__)

# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
class ContractList(object) :
    """A class to store information about contract code files
    """

    # -----------------------------------------------------------------
    @classmethod
    def load(cls, config) :
        """Compute a list of URLs for known contracts
        """
        root = Contract.__root_directory__(config)
        contract_files = glob.glob('{0}/*.pdo'.format(root))

        contract_list = cls(config)
        for contract_file in contract_files :
            contract = Contract.load(config, contract_file, use_raw=True)
            contract_list.add(contract)

        return contract_list

    # -----------------------------------------------------------------
    def __init__(self, config) :
        self.config = config
        self.__by_name__ = {}
        self.__by_contract_id__ = {}

    # -----------------------------------------------------------------
    def __iter__(self) :
        for contract_id, contract in self.__by_contract_id__.items() :
            yield contract

    # -----------------------------------------------------------------
    def get_by_name(self, name) :
        contract_id =  self.__by_name__[name]
        return self.__by_contract_id__[contract_id]

    # -----------------------------------------------------------------
    def get_by_contract_id(self, contract_id) :
        return self.__by_contract_id__[contract_id]

    # -----------------------------------------------------------------
    def add(self, contract) :
        self.__by_name__[contract.name] = contract.contract_id
        self.__by_contract_id__[contract.contract_id] = contract

    # -----------------------------------------------------------------
    @property
    def count(self) :
        return len(self.__by_contract_id__)

# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
class Contract(pdo_contract) :
    """A class to store information about an enclave service
    """
    # -----------------------------------------------------------------
    @staticmethod
    def __root_directory__(config) :
        """Pull the enclave service data directory from the
        configuration file.
        """
        path_config = config.get('ContentPaths', {})
        return os.path.realpath(path_config.get('Contract', os.path.join(os.environ['HOME'], '.toxaway')))

    # -----------------------------------------------------------------
    @staticmethod
    def __file_name__(config, contract_id) :
        """create the name of the file for storing the profile
        """
        root = Contract.__root_directory__(config)
        contract_id = contract_id.replace('+','-').replace('/','_')
        return os.path.realpath(os.path.join(root, '{0}.pdo'.format(os.path.basename(contract_id))))

    # -----------------------------------------------------------------
    @classmethod
    def import_contract(cls, config, contract_file, contract_name) :
        """create a new contract pdo object and save it
        """

        try :
            contract_info = json.load(contract_file)
        except :
            logger.warn('failed to retrieve contract information')
            return None

        try :
            code_info = contract_info['contract_code']
            code = pdo_contract_code(code_info['Code'], code_info['Name'], code_info['Nonce'])
        except KeyError as ke :
            logger.error('invalid contract data file; missing %s', str(ke))
            raise Exception("invalid contract file; {}".format())
        except Exception as e :
            logger.error('error occurred retreiving contract code; %s', str(e))
            raise Exception("invalid contract file; {}".format(contract_name))

        ## need to handle the case where the contract has been registered
        ## but the initial state has not been committed

        ledger_config = config.get('Sawtooth', {})
        try :
            contract_id = contract_info['contract_id']
            current_state_hash = pdo_contract_state.get_current_state_hash(ledger_config, contract_id)
        except Exception as e :
            logger.error('error occurred retreiving contract state hash; %s', str(e))
            raise Exception('invalid contract file; {}'.format(contract_name))

        try :
            path_config = config.get('ContentPaths')
            state_root = os.path.realpath(path_config.get('State', os.path.join(os.environ['HOME'], '.toxaway')))

            state = pdo_contract_state.read_from_cache(contract_id, current_state_hash, data_dir=state_root)
            if state is None :
                state = pdo_contract_state.get_from_ledger(ledger_config, contract_id, current_state_hash)
                state.save_to_cache(data_dir=data_dir)
        except Exception as e :
            logger.error('error occurred retreiving contract state; %s', str(e))
            raise Exception("invalid contract file; {}".format(contract_name))

        extra_data = contract_info.get('extra_data', {})
        extra_data['name'] = contract_name
        extra_data['update-enclave'] = 'random'
        extra_data['invoke-enclave'] = 'random'

        obj = cls(code, state, contract_info['contract_id'], contract_info['creator_id'], extra_data=extra_data)
        for enclave in contract_info['enclaves_info'] :
            obj.set_state_encryption_key(
                enclave['contract_enclave_id'],
                enclave['encrypted_contract_state_encryption_key'])

        obj.save(config)
        return obj

    # -----------------------------------------------------------------
    @classmethod
    def load(cls, config, code_file_name, use_raw=False) :
        """load an existing contract from disk
        """
        if not use_raw :
            code_file_name = Contract.__file_name__(config, code_file_name)
        if not os.path.exists(code_file_name) :
            return None

        path_config = config.get('ContentPaths')
        state_root = os.path.realpath(path_config.get('State', os.path.join(os.environ['HOME'], '.toxaway')))

        logger.info('load from %s', code_file_name)
        return cls.read_from_file(config['Sawtooth'], code_file_name, data_dir=state_root)

    # -----------------------------------------------------------------
    def __init__(self, code, state, contract_id, creator_id, **kwargs) :
        pdo_contract.__init__(self, code, state, contract_id, creator_id, **kwargs)

    # -----------------------------------------------------------------
    @property
    def safe_contract_id(self) :
        return self.contract_id.replace('+','-').replace('/','_')

    # -----------------------------------------------------------------
    @property
    def name(self) :
        return self.extra_data.get('name', self.short_id)

    @name.setter
    def name(self, n) :
        self.extra_data['name'] = n

    # -----------------------------------------------------------------
    @property
    def invoke_enclave(self) :
        return self.extra_data.get('invoke-enclave', 'random')

    @property
    def safe_invoke_enclave(self) :
        return hashlib.sha256(self.invoke_enclave.encode('utf8')).hexdigest()[:16]

    @invoke_enclave.setter
    def invoke_enclave(self, e) :
        logger.info('invoke list: %s', list(self.provisioned_enclaves))
        if e not in list(self.provisioned_enclaves) + ['random'] :
            raise ValueError('default invocation enclave not provisioned')
        self.extra_data['invoke-enclave'] = e

    # -----------------------------------------------------------------
    @property
    def update_enclave(self) :
        return self.extra_data.get('update-enclave', 'random')

    @property
    def safe_update_enclave(self) :
        return hashlib.sha256(self.update_enclave.encode('utf8')).hexdigest()[:16]

    @update_enclave.setter
    def update_enclave(self, e) :
        logger.info('update list: %s', list(self.provisioned_enclaves))
        if e not in list(self.provisioned_enclaves) + ['random'] :
            raise ValueError('default invocation enclave not provisioned')
        self.extra_data['update-enclave'] = e

    # -----------------------------------------------------------------
    def enclave_reference_map(self) :
        for enclave_id, encrypted_key in self.enclave_map.items() :
            hashed_identity = hashlib.sha256(enclave_id.encode('utf8')).hexdigest()[:16]
            result = []
            for x in range(0, len(encrypted_key), 75) :
                result.append(encrypted_key[x:x+75])
            yield (hashed_identity, "\n".join(result))

    # -----------------------------------------------------------------
    def save(self, config) :
        """serialize the contract, encrypt it and write it to disk
        """
        code_file_name = Contract.__file_name__(config, self.contract_id)

        code_path = os.path.dirname(code_file_name)
        if not os.path.isdir(code_path) :
            os.makedirs(code_path)

        self.save_to_file(code_file_name)

# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
class LedgerContract(object) :
    """A class to store information about an enclave service
    """

    # -----------------------------------------------------------------
    @classmethod
    def load(cls, config, contract_id) :
        """Compute a list of URLs for known contracts
        """

        ledger_config = config["Sawtooth"]
        client = pdo_connect.PdoRegistryHelper(ledger_config['LedgerURL'])

        try :
            contract_info = client.get_contract_dict(contract_id)
        except Exception as e :
            logger.info('error getting state hash; %s', str(e))
            raise Exception('failed to retrieve contract state hash; {}'.format(contract_id))
        logger.info("contract_info: %s", contract_info)

        try :
            ccl_info = client.get_ccl_info_dict(contract_id)
            current_state_hash = ccl_info['current_state']['state_hash']
        except Exception as e :
            logger.info('error getting state hash; %s', str(e))
            raise Exception('failed to retrieve contract state hash; {}'.format(contract_id))
        logger.info("ccl_info: %s", ccl_info)

        try :
            state_info = client.get_ccl_state_dict(contract_id, current_state_hash)
        except Exception as e :
            logger.info('error getting state; %s', str(e))
            raise Exception('failed to retrieve contract state; {}', contract_id)
        logger.info("state_info: %s", state_info)

        return cls(contract_info, ccl_info, state_info)

    # -----------------------------------------------------------------
    def __init__(self, contract_info, ccl_info, state_info) :
        self.contract_info = contract_info
        self.ccl_info = ccl_info
        self.state_info = state_info
