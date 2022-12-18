from django.shortcuts import render
from django.http import HttpResponse
import pyrebase
from pathlib import Path
import os
from data_service.data_modifier import DataModifier
from data_service.data_manager import DataManager, UserCreator
import json
from datetime import date, datetime


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


def get_expiry_drugs(drugs_dict: dict, return_n: int = 4):
    today = datetime.today()
    date_distance = []
    for (k, v) in drugs_dict.items():
        d_date = datetime.strptime(v["expiration_date"], "%d-%m-%Y %H:%M %p")
        dist = (d_date - today).days
        date_distance.append((k, dist))

    date_distance.sort(key=lambda x: x[1])
    exp_drugs = {}
    for tup in date_distance[:return_n]:
        exp_drugs[tup[0]] = drugs_dict.get(tup[0])

    exp_drugs = {k: v for k, v in sorted(exp_drugs.items(), key=lambda item: item[1]["expiration_date"])}

    return exp_drugs


def get_user_statistics(user_dict: dict):
    drugs_dict = user_dict["drugs"]

    tup = {}
    for (k, v) in drugs_dict.items():
        if k not in tup.keys():
            tup[k] = v["pills_left"]
        else:
            tup[k] += v["pills_left"]

    tup = {k: v for k, v in sorted(tup.items(), key=lambda item: item[1])}

    # Most pills medicine
    user_dict["most_pills"] = [drugs_dict[list(tup.keys())[-1]]["active_principle"], list(tup.values())[-1]]

    # Less pills medicine
    user_dict["least_pills"] = [drugs_dict[list(tup.keys())[0]]["active_principle"], list(tup.values())[0]]

    most_expensive = ['a', -99999]
    cheapest = ['a', 99999]
    for (k, v) in drugs_dict.items():
        if v["pvp"] >= most_expensive[1]:
            most_expensive = [v["active_principle"], v["pvp"]]

        if v["pvp"] <= cheapest[1]:
            cheapest = [v["active_principle"], v["pvp"]]

    # Most expensive medicine
    user_dict["most_expensive_drug"] = most_expensive

    # Cheapest medicine
    user_dict["cheapest_drug"] = cheapest

    return user_dict


def home_view(request, *args, **kwargs):
    return render(request, 'home_page.html', {})


def log_in_view(request, *args, **kwargs):
    return render(request, 'login.html', {})


def user_patient_view(request, *args, **kwargs):
    print('SESSION UID:', request.session['uid'], '======================')
    return render(request, 'user_patient.html', {})


def post_sign_in(request, *args, **kwargs):
    email = request.POST.get('email')
    passw = request.POST.get('pass')
    try:
        # if there is no error then signin the user with given email and password
        user = auth.sign_in_with_email_and_password(email, passw)
        uid = user['localId']
    except:
        print(email, passw)
        message = "Invalid Credentials"
        return render(request, "login.html", {"message": message})

    session_id = user['idToken']
    # request.session['uid'] = str(session_id)
    user_info = db.child('users').child('patients').get(uid).val()[uid]
    user_info["expiry_drugs"] = get_expiry_drugs(user_info["drugs"])
    user_info = get_user_statistics(user_dict=user_info)
    return render(request, "user_patient.html", context=user_info)


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
