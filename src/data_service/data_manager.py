import json
import pyrebase
import pandas as pd
import numpy as np
import random
import firebase_admin
from firebase_admin import credentials, firestore
from urllib.request import urlopen
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class DataManager:
    def __init__(self):
        self.config = {
            "apiKey": "AIzaSyCX-UYV_jRURt6cqFGyOQdQ9I4nHvVJAuQ",
            "authDomain": "medicine-smart-box.firebaseapp.com",
            "databaseURL": "https://medicine-smart-box-default-rtdb.europe-west1.firebasedatabase.app",
            "projectId": "medicine-smart-box",
            "storageBucket": "medicine-smart-box.appspot.com",
            "messagingSenderId": "567670754202",
            "appId": "1:567670754202:web:3119c752d712996ac4c823",
            "serviceAccount": os.path.join(BASE_DIR, 'keys/medicine-smart-box-firebase-adminsdk-bahpt-88cbcbb75b.json')
        }
        self.firebase = pyrebase.initialize_app(self.config)
        self.storage = self.firebase.storage()
        self.db = self.firebase.database()

    def load_file_to_db_child(self, child: str, where_from: str, file_name: str):
        with open(f'{where_from}/{file_name}', 'r') as file:
            contents = json.load(file)
        self.db.child(child).set(contents)

    def get_file_from_db_child(self, child: str, file_name: str):
        data = self.db.child(child).get()
        with open(f'json_files/{file_name}', 'w') as file:
            json.dump(data.val(), file)

    def push_files_to_storage(self, where_from: str, where_to: str, file_names: list[str]):
        for fn in file_names:
            self.storage.child(f'{where_to}/{fn}').put(f'{where_from}/{fn}')

    def get_files_from_storage(self, where_from: str, where_to: str):
        all_files = self.storage.child(f'{where_from}/').list_files()
        for file in all_files:
            if file.name.split('.')[-1] == 'json':
                try:
                    file.download_to_filename(f'{where_to}/{file.name}')
                except:
                    print(f'Download for {file.name} Failed')


class ProductCreator:
    def __init__(self, active_principles: list[str] = None):
        self.df = pd.DataFrame()
        self.drugs_dict = {}
        self.principles = active_principles
        self.dm = DataManager()

    def _load_csv(self):
        url = self.dm.storage.child("medicine_data/medicaments.csv").get_url(None)
        self.df = pd.read_csv(url, encoding="ISO-8859-1", sep=';')
        self.df = self.df[self.df['Estado'] == 'ALTA']
        self.df['Principio activo o asociaciÃ³n de principios activos'] = self.df['Principio activo o asociaciÃ³n de principios activos'].str.replace(',','')
        self.df['Principio activo o asociaciÃ³n de principios activos'] = self.df['Principio activo o asociaciÃ³n de principios activos'].str.lower()

    def _select_drugs(self):
        return self.df[self.df['Principio activo o asociaciÃ³n de principios activos'].isin(self.principles)]

    def build_drugs_dict(self, verbose: bool = False, out_file: str = ''):
        self._load_csv()
        drugs_df = self._select_drugs()
        for p in self.principles:
            slice = drugs_df[drugs_df['Principio activo o asociaciÃ³n de principios activos'].isin([p])]
            if not slice.empty:
                item = slice.iloc[0]
                self.drugs_dict[str(item['Código Nacional'])] = {
                    "name": item['Nombre del producto farmacéutico'],
                    "active_principle": item['Principio activo o asociaciÃ³n de principios activos'],
                    "pvp": item['Precio venta al público con IVA']
                }

        if verbose:
            print(self.drugs_dict)

        with open(f'json_files/{out_file}', 'w') as file:
            json.dump(self.drugs_dict, file)


class UserCreator:
    def __init__(self, n_patients: int = 5, n_hcp: int = 2):
        self.n_patients = n_patients
        self.n_hcp = n_hcp
        self.dm = DataManager()
        self.patients_dict = {}
        self.hcp_dict = {}
        self.users_dict = {
            "patients": {},
            "hcp": {}
        }

    def _load_patients(self):
        url = self.dm.storage.child("base_users/patients.json").get_url(None)
        self.patients_dict = json.loads(urlopen(url).read())

    def _load_hcp(self):
        url = self.dm.storage.child("base_users/hcp.json").get_url(None)
        self.hcp_dict = json.loads(urlopen(url).read())

    def _fill_patients_drugs(self):
        url = self.dm.storage.child("medicine_data/drugs_dict.json").get_url(None)
        drugs_dict = json.loads(urlopen(url).read())
        drug_ids = list(drugs_dict.keys())
        for (k, v) in self.patients_dict.items():
            self.patients_dict[k]['drugs'] = random.choices(drug_ids, k=np.random.randint(1, 12))

    def build_users_dict(self, verbose: bool = False, out_file: str = ''):
        self._load_patients()
        self._load_hcp()
        self._fill_patients_drugs()
        self.users_dict['patients'] = self.patients_dict
        self.users_dict['hcp'] = self.hcp_dict

        if verbose:
            print(self.users_dict)

        with open(f'json_files/patients.json', 'w') as file:
            json.dump(self.patients_dict, file)

        with open(f'json_files/hcp.json', 'w') as file:
            json.dump(self.hcp_dict, file)

        with open(f'json_files/{out_file}', 'w') as file:
            json.dump(self.users_dict, file)


def initialize_database_and_storage(dm: DataManager = DataManager(),
                                    pc: ProductCreator = ProductCreator(),
                                    uc: UserCreator = UserCreator()):
    prod_file = 'drugs_dict.json'

    pc.build_drugs_dict(out_file=prod_file)

    uc.build_users_dict(out_file='users.json')

    # Uploading files to storage:
    dm.push_files_to_storage(where_from='json_files', where_to='medicine_data', file_names=['drugs_dict.json'])
    dm.push_files_to_storage(where_from='json_files', where_to='base_users',
                             file_names=['patients.json', 'hcp.json', 'users.json'])

    # Uploading data to db:
    dm.load_file_to_db_child(child='users', where_from='json_files', file_name='users.json')
    dm.load_file_to_db_child(child='drugs', where_from='json_files', file_name='drugs_dict.json')

    print('Process finished with no errors')


def overwrite_json_files(dm: DataManager = DataManager()):
    dm.get_files_from_storage(where_from='base_users', where_to='json_files')
    dm.get_files_from_storage(where_from='medicine_data', where_to='json_files')


# TODO: add functions to add/delete unique elements (either drugs or patients/hcp) to db
if __name__ == "__main__":
    principles = [
        'ibu',
        'paracetamol',
        'pramipexol',
        'pramipexol',
        'rifabutina',
        'rufinamida',
        'letrozol',
        'epinefrina',
        'diazepam',
        'acexamato zinc',
        'paroxetina',
        'lidocaina',
        'rizatriptan',
        'glucosamina',
        'cefixima'
    ]
    DM = DataManager()
    PC = ProductCreator(active_principles=principles)
    UC = UserCreator()

    action = 'initialize_db_and_storage'

    if action == 'initialize_db_and_storage':
        initialize_database_and_storage(dm=DM, pc=PC, uc=UC)
    elif action == 'overwrite_json_files':
        overwrite_json_files(dm=DM)


