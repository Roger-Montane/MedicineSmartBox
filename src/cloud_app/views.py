from django.shortcuts import render
from django.http import HttpResponse
import pyrebase
from pathlib import Path
import os
from data_service.data_modifier import DataModifier
from data_service.data_manager import DataManager, UserCreator
import json


BASE_DIR = Path(__file__).resolve().parent.parent.parent
config = {
    "apiKey": "AIzaSyCX-UYV_jRURt6cqFGyOQdQ9I4nHvVJAuQ",
    "authDomain": "medicine-smart-box.firebaseapp.com",
    "databaseURL": "https://medicine-smart-box-default-rtdb.europe-west1.firebasedatabase.app",
    "projectId": "medicine-smart-box",
    "storageBucket": "medicine-smart-box.appspot.com",
    "messagingSenderId": "567670754202",
    "appId": "1:567670754202:web:3119c752d712996ac4c823",
    "serviceAccount": os.path.join(BASE_DIR, 'keys/medicine-smart-box-firebase-adminsdk-bahpt-88cbcbb75b.json')
}
firebase = pyrebase.initialize_app(config)
storage = firebase.storage()
db = firebase.database()
auth = firebase.auth()


def sanity_check(user_type: str, key: str = 'default'):
    uc = UserCreator()
    if user_type == 'patient':
        uc._load_patients(load_from='file')
        del uc.patients_dict[key]
        with open(os.path.join(BASE_DIR, 'src/data_service/json_files/patients.json'), 'w') as file:
            json.dump(uc.patients_dict, file)
    elif user_type == 'hcp':
        uc._load_hcp(load_from='file')
        del uc.hcp_dict[key]
        with open(os.path.join(BASE_DIR, 'src/data_service/json_files/hcp.json'), 'w') as file:
            json.dump(uc.hcp_dict, file)

    uc.build_users_dict(out_file=os.path.join(BASE_DIR, 'src/data_service/json_files'), )
    dm = DataManager()
    dm.update_file_to_db_child(child='users', where_from='json_files', file_name='users.json')


def home_view(request, *args, **kwargs):
    return render(request, 'home_page.html', {})


def log_in_view(request, *args, **kwargs):
    return render(request, 'login.html', {})


def user_patient_view(request, *args, **kwargs):
    return render(request, 'user_patient.html', {})


def post_sign_in(request, *args, **kwargs):
    email = request.POST.get('email')
    passw = request.POST.get('pass')
    try:
        # if there is no error then signin the user with given email and password
        user = auth.sign_in_with_email_and_password(email, passw)
    except:
        print(email, passw)
        message = "Invalid Credentials"
        return render(request, "login.html", {"message": message})

    session_id = user['idToken']
    request.session['uid'] = str(session_id)
    return render(request, "user_patient.html", {"email": email})


def patient_sign_up(request, *args, **kwargs):
    return render(request, "patient_signup.html")


def hcp_sign_up(request, *args, **kwargs):
    return render(request, "hcp_signup.html")


def logout(request, *args, **kwargs):
    try:
        del request.session['uid']
    except:
        pass
    return render(request, "login.html")


def patient_post_sign_up(request, *args, **kwargs):
    email = request.POST.get('email')
    passw = request.POST.get('pass')
    name = request.POST.get('name')
    age = request.POST.get('name')
    phone = request.POST.get('phone')

    try:
        # creating a user with the given email and password
        user = auth.create_user_with_email_and_password(email, passw)
        uid = user['localId']
        idtoken = request.session['uid']
        print(uid)
        # user_dict = {
        #     "age": age, "credentials": {"email": email, "password": passw}, "drugs": {}, "phone": phone, "name": name
        # }
        # DM = DataModifier()
        # DM.add_user(user_type="patient", user_info=user_dict)
    except:
        message = "Something went wrong, try again"
        return render(request, "patient_signup.html", {"message": message})

    try:
        user_dict = {
            "age": age, "credentials": {"email": email, "password": passw}, "drugs": "None", "phone": phone, "name": name
        }
        DM = DataModifier()
        DM.add_user(user_type="patient", user_info=user_dict, key=uid)
    except:
        auth.delete_user_account(id_token=uid)
        sanity_check(user_type='patient', key=uid)
        message = "Patient could not be created in database, deleting..."
        return render(request, "patient_signup.html", {"message": message})

    return render(request, "login.html")


def hcp_post_sign_up(request, *args, **kwargs):
    email = request.POST.get('email')
    passw = request.POST.get('pass')
    name = request.POST.get('name')
    age = request.POST.get('name')
    phone = request.POST.get('phone')

    try:
        # creating a user with the given email and password
        user = auth.create_user_with_email_and_password(email, passw)
        uid = user['localId']
        idtoken = request.session['uid']
        print(uid)
    except:
        message = "Something went wrong, try again"
        return render(request, "hcp_signup.html", {"message": message})

    try:
        user_dict = {
            "age": age, "credentials": {"email": email, "password": passw}, "patients": "None", "phone": phone, "name": name
        }
        DM = DataModifier()
        DM.add_user(user_type="hcp", user_info=user_dict, key=uid)
    except:
        auth.delete_user_account(id_token=uid)
        sanity_check(user_type='hcp', key=uid)
        message = "HCP could not be created in database, deleting..."
        return render(request, "patient_signup.html", {"message": message})

    return render(request, "login.html")


if __name__ == "__main__":
    print(BASE_DIR)
