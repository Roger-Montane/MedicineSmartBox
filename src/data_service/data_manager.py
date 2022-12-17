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

    def update_file_to_db_child(self, child: str, where_from: str, file_name: str):
        with open(f'{where_from}/{file_name}', 'r') as file:
            contents = json.load(file)
        self.db.child(child).update(contents)

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
        self.df['Principio activo o asociaciÃ³n de principios activos'] = self.df[
            'Principio activo o asociaciÃ³n de principios activos'].str.replace(',', '')
        self.df['Principio activo o asociaciÃ³n de principios activos'] = self.df[
            'Principio activo o asociaciÃ³n de principios activos'].str.lower()

    def _select_drugs(self):
        return self.df[self.df['Principio activo o asociaciÃ³n de principios activos'].isin(self.principles)]

    def _filter_from_df(self):
        drugs_df = self.df[self.df['Nombre de la agrupaciÃ³n homogÃ©nea del producto sanitario'] != '']
        drugs_df['Nombre de la agrupaciÃ³n homogÃ©nea del producto sanitario'] = drugs_df[
            'Nombre de la agrupaciÃ³n homogÃ©nea del producto sanitario'].astype(str)
        drugs_df = drugs_df[drugs_df['Nombre de la agrupaciÃ³n homogÃ©nea del producto sanitario'].str.lower() != 'nan']
        return drugs_df.reset_index()

    def build_drugs_dict(self, verbose: bool = False, out_file: str = '', max_n_drugs: int = 30):
        self._load_csv()
        # drugs_df = self._select_drugs()
        drugs_df = self._filter_from_df()
        self.principles = drugs_df['Nombre de la agrupaciÃ³n homogÃ©nea del producto sanitario'].unique()
        self.principles = [p for p in self.principles if len(p.split(' ')) >= 5]
        self.principles = self.principles[:max_n_drugs]
        for p in self.principles:
            slice = drugs_df[drugs_df['Principio activo o asociaciÃ³n de principios activos'].isin(
                [p.lower().split(' ')[0]])]
            if not slice.empty:
                item = slice.iloc[0]
                agrupation_name = p.split(' ')
                try:
                    n_caps = str(int(agrupation_name[3]))
                except ValueError:
                    n_caps = str(25)
                self.drugs_dict[str(item['Código Nacional'])] = {
                    "name": item['Nombre del producto farmacéutico'],
                    "active_principle": ' '.join(agrupation_name[:3]),
                    # "active_principle": item['Principio activo o asociaciÃ³n de principios activos'],
                    "n_capsules": n_caps,
                    "pvp": item['Precio venta al público con IVA']
                }

        if verbose:
            print('Drugs dict:')
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

    @staticmethod
    def random_date(start: datetime, end: datetime):
        delta = end - start
        int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
        random_second = random.randrange(int_delta)
        return start + datetime.timedelta(seconds=random_second)

    def _get_pills_and_name(self, prod_id: str):
        drug_info = {}
        with open('json_files/drugs_dict.json', 'r') as file:
            drug_info = json.load(file)

        d = {}
        prod = drug_info[prod_id]
        n_capsules = drug_info[prod_id]['n_capsules']
        if not n_capsules.split(' ')[0].isnumeric():
            d["n_capsules"] = "-"
        else:
            d["n_capsules"] = n_capsules
        d["name"] = prod["name"].split(',')[0]
        d["active_principle"] = prod["active_principle"]
        d["pvp"] = prod["pvp"]

        return d

    def _fill_drug_info(self, prod_id: str):
        curr_year = datetime.date.today().year
        t_format = '%d-%m-%Y %H:%M %p'
        start_d = datetime.datetime.strptime(f'01-01-{curr_year} 00:01 AM', t_format)
        end_d = datetime.datetime.strptime(f'31-12-{curr_year} 23:59 PM', t_format)
        date_logged_in = self.random_date(start=start_d, end=end_d)

        date_logged_out = ''
        if random.choice([0, 1]):
            date_logged_out = self.random_date(start=date_logged_in,
                                               end=date_logged_in.replace(year=date_logged_in.year + 1))

        expiration_date = self.random_date(start=date_logged_in,
                                           end=date_logged_in.replace(year=date_logged_in.year + 1))

        d = self._get_pills_and_name(prod_id=prod_id)
        out = {
            "date_logged_in": date_logged_in.strftime(t_format),
            "date_logged_out": '-' if date_logged_out == '' else date_logged_out.strftime(t_format),
            "expiration_date": expiration_date.strftime(t_format),
            "pills_left": d["n_capsules"],
            "name": d["name"],
            "pvp": d["pvp"],
            "active_principle": d["active_principle"]
        }

        return out

    def _load_patients(self, load_from: str = "file"):
        if load_from == "storage":
            url = self.dm.storage.child("base_users/patients.json").get_url(None)
            self.patients_dict = json.loads(urlopen(url).read())
        elif load_from == "file":
            with open('json_files/patients.json', 'r') as file:
                self.patients_dict = json.load(file)

    def _load_hcp(self, load_from: str = "file"):
        if load_from == "storage":
            url = self.dm.storage.child("base_users/hcp.json").get_url(None)
            self.hcp_dict = json.loads(urlopen(url).read())
        elif load_from == "file":
            with open('json_files/hcp.json', 'r') as file:
                self.hcp_dict = json.load(file)

    def _fill_patients_drugs(self, load_from: str = "file"):
        if load_from == "storage":
            url = self.dm.storage.child("medicine_data/drugs_dict.json").get_url(None)
            drugs_dict = json.loads(urlopen(url).read())
        elif load_from == "file":
            with open('json_files/drugs_dict.json', 'r') as file:
                drugs_dict = json.load(file)
        drug_ids = list(drugs_dict.keys())
        for (k, v) in self.patients_dict.items():
            self.patients_dict[k]['drugs'] = {}
            drugs = random.choices(drug_ids, k=np.random.randint(6, 20))
            for d in drugs:
                self.patients_dict[k]['drugs'][d] = self._fill_drug_info(prod_id=d)
            # self.patients_dict[k]['drugs'] = random.choices(drug_ids, k=np.random.randint(6, 20))

    def build_users_dict(self, verbose: bool = False, out_file: str = '', load_from: str = "file"):
        self._load_patients(load_from=load_from)
        self._load_hcp(load_from=load_from)
        self._fill_patients_drugs(load_from=load_from)
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

    def sanity_check(self, user_type: str, key: str = 'default'):
        if user_type == 'patient':
            self._load_patients(load_from='file')
            del self.patients_dict[key]
        elif user_type == 'hcp':
            self._load_hcp(load_from='file')
            del self.hcp_dict[key]


def load_database_and_storage(dm: DataManager = DataManager(),
                              pc: ProductCreator = ProductCreator(),
                              uc: UserCreator = UserCreator(),
                              method: str = "load"):
    prod_file = 'drugs_dict.json'

    print("Building drugs_dict...", end=" ")
    pc.build_drugs_dict(out_file=prod_file, verbose=True)
    print("DONE")
    # print("Pushing 'json_files/drugs_dict.json' to storage...", end=" ")
    # dm.push_files_to_storage(where_from='json_files', where_to='medicine_data', file_names=['drugs_dict.json'])
    # print("DONE")

    print("Uploading drugs data to db...", end=" ")
    if method == "load":
        dm.load_file_to_db_child(child='drugs', where_from='json_files', file_name='drugs_dict.json')
    elif method == "update":
        dm.update_file_to_db_child(child='drugs', where_from='json_files', file_name='drugs_dict.json')
    print("DONE\n------------------------------------------------")

    print("Building users_dict...", end=" ")
    uc.build_users_dict(out_file='users.json', load_from='file')
    print("DONE")
    # print("Pushing 'json_files/[patients.json, hcp.json, users.json]' to storage...", end=" ")
    # dm.push_files_to_storage(where_from='json_files', where_to='base_users',
    #                          file_names=['patients.json', 'hcp.json', 'users.json'])
    # print("DONE")

    print("Uploading users data to db...", end=" ")
    if method == "load":
        dm.load_file_to_db_child(child='users', where_from='json_files', file_name='users.json')
    elif method == "update":
        dm.update_file_to_db_child(child='users', where_from='json_files', file_name='users.json')
    print("DONE\n------------------------------------------------")

    print('Process finished with no errors')


def overwrite_json_files(dm: DataManager = DataManager()):
    dm.push_files_to_storage(where_from='json_files', where_to='base_users',
                             file_names=['users.json', 'hcp.json', 'patients.json'])
    dm.push_files_to_storage(where_from='json_files', where_to='medicine_data',
                             file_names=['drugs_dict.json'])


def get_files_from_storage(dm: DataManager = DataManager()):
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
        load_database_and_storage(dm=DM, pc=PC, uc=UC, method="update")
    elif action == 'overwrite_json_files':
        overwrite_json_files(dm=DM)
    elif action == 'get_files_from_storage':
        get_files_from_storage(dm=DM)
