import json
import pyrebase
import pandas as pd
import numpy as np
import firebase_admin
from firebase_admin import credentials, firestore
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

    def load_file_to_db_child(self, child: str, file_name: str):
        with open(f'json_files/{file_name}', 'r') as file:
            contents = json.load(file)
        self.db.child(child).set(contents)

    def get_file_from_db_child(self, child: str, file_name: str):
        data = self.db.child(child).get()
        with open(f'json_files/{file_name}', 'w') as file:
            json.dump(data.val(), file)



class UserCreator:
    pass


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
        for p in principles:
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
        'glucosamina'
    ]
    prod_file = 'drugs_dict.json'

    dm = DataManager()
    uc = UserCreator()
    pc = ProductCreator(active_principles=principles)

    pc.build_drugs_dict(out_file=prod_file)

    dm.load_file_to_db_child(child='drugs', file_name=prod_file)
    # dm.load_file_to_db_child(child='users', file_name='users_mock.json')
    # dm.get_file_from_db_child(child='users', file_name='output.json')
