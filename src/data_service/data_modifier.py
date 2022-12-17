import json
import pyrebase
import pandas as pd
import numpy as np
import random
import time
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from urllib.request import urlopen
from data_service.data_manager import DataManager
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class DataModifier:
    def __init__(self):
        self.patients_file = os.path.join(BASE_DIR, 'src/data_service/json_files/patients.json')
        self.hcp_file = os.path.join(BASE_DIR, 'src/data_service/json_files/hcp.json')
        self.users_file = os.path.join(BASE_DIR, 'src/data_service/json_files/users.json')
        self.drugs_file = os.path.join(BASE_DIR, 'src/data_service/json_files/drugs_dict.json')
        self.data_manager = DataManager()

    def _add_patient(self, patient_info: dict, upload: bool = True, key: str = 'default'):
        patients_dict = {}
        with open(self.patients_file, 'r+') as file:
            patients_dict = json.load(file)

        # key = str(int(list(patients_dict.keys())[-1]) + 1)
        patients_dict[key] = patient_info

        with open(self.patients_file, 'w') as file:
            json.dump(patients_dict, file)

        if upload:
            self.data_manager.push_files_to_storage(where_from=os.path.join(BASE_DIR, 'src/data_service/json_files'),
                                                    where_to='base_users',
                                                    file_names=['patients.json'])

    def _add_hcp(self, hcp_info: dict, upload: bool = True, key: str = 'default'):
        hcp_dict = {}
        with open(self.hcp_file, 'r') as file:
            hcp_dict = json.load(file)

        # key = str(int(list(hcp_dict.keys())[-1]) + 1)
        hcp_dict[key] = hcp_info

        with open(self.hcp_file, 'w') as file:
            json.dump(hcp_dict, file)

        if upload:
            self.data_manager.push_files_to_storage(where_from=os.path.join(BASE_DIR, 'src/data_service/json_files'),
                                                    where_to='base_users',
                                                    file_names=['hcp.json'])

    def add_user(self, user_type: str, user_info: dict, upload: bool = True, key: str = 'default', verbose: bool = True):
        if not bool(user_info):
            print('Data is empty! Stopping')
            return

        if user_type == 'patient':
            self._add_patient(patient_info=user_info, upload=upload, key=key)
        elif user_type == 'hcp':
            self._add_hcp(hcp_info=user_info, upload=upload, key=key)

        patients_dict = {}
        with open(self.patients_file, 'r') as file:
            patients_dict = json.load(file)

        hcp_dict = {}
        with open(self.hcp_file, 'r') as file:
            hcp_dict = json.load(file)

        users_dict = {
            "patients": patients_dict,
            "hcp": hcp_dict
        }

        with open(self.users_file, 'w') as file:
            json.dump(users_dict, file)

        if upload:
            self.data_manager.push_files_to_storage(where_from=os.path.join(BASE_DIR, 'src/data_service/json_files'),
                                                    where_to='base_users',
                                                    file_names=['users.json'])
            self.data_manager.load_file_to_db_child(child='users',
                                                    where_from=os.path.join(BASE_DIR, 'src/data_service/json_files'),
                                                    file_name='users.json')

        if verbose:
            print(f'{user_type} {list(user_info.keys())[0]} added successfully')

    def add_drug(self, drug_info: dict, upload: bool = True, verbose: bool = True):
        if not bool(drug_info):
            print('Data is empty! Stopping')
            return

        drugs_dict = {}
        with open(self.drugs_file, 'r') as file:
            drugs_dict = json.load(file)

        key = list(drug_info.keys())[0]
        drugs_dict[key] = drug_info[key]

        with open(self.drugs_file, 'w') as file:
            json.dump(drugs_dict, file)

        if upload:
            self.data_manager.push_files_to_storage(where_from='json_files', where_to='medicine_data',
                                                    file_names=['drugs_dict.json'])
            self.data_manager.load_file_to_db_child(child='drugs', where_from='json_files', file_name='drugs_dict.json')

        if verbose:
            print(f'Drug {key} added successfully')

    def consume_drug(self, user_id: str, prod_id: str, n_units: int = 1, verbose: bool = True):
        users_dict = {}
        with open(self.users_file, 'r') as file:
            users_dict = json.load(file)

        patients_dict = users_dict['patients']
        my_patient = patients_dict[user_id]
        if prod_id in my_patient['drugs']:
            my_patient['drugs'][prod_id]['pills_left'] = str(int(my_patient['drugs'][prod_id]['pills_left']) - n_units)

        users_dict['patients'][user_id] = my_patient
        patients_dict[user_id] = my_patient

        with open(self.users_file, 'w') as file:
            json.dump(users_dict, file)

        with open(self.patients_file, 'w') as file:
            json.dump(patients_dict, file)

        self.data_manager.push_files_to_storage(where_from='json_files', where_to='base_users',
                                                file_names=['users.json', 'patients.json'])
        self.data_manager.load_file_to_db_child(child='users', where_from='json_files', file_name='users.json')

        if verbose:
            print(f'User {user_id} has consumed {n_units} {"unit" if n_units == 1 else "units"} of drug {prod_id}')


if __name__ == "__main__":
    data_mod = DataModifier()
    # data_mod.add_user(user_type='patient', user_info={})
    data_mod.consume_drug(user_id='1', prod_id='652223')
