from datetime import datetime

import pyrebase
import pytz
import requests
# from celery import shared_task
from django.conf import settings
# from fake_useragent import UserAgent
from pyfcm import FCMNotification


# @shared_task(name="tracker")
def my_cowin_runner():
    def call(pin_code, date, execute_18_plus, initial_18_plus_slot_date, execute_45_plus, initial_45_plus_slot_date):

        url = 'https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByPin?pincode=' + pin_code + '&date=' + date
        # ua = UserAgent()

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
        }

        response = requests.get(url, headers=headers)
        print("Json response Code")
        print(response.status_code)
        response.content.decode()

        is_slot_available_in_18_plus = False
        is_slot_available_in_45_plus = False
        available_slot_date_in_18_plus = initial_18_plus_slot_date
        available_slot_date_in_45_plus = initial_45_plus_slot_date

        json_response = response.json()
        all_centers = json_response["centers"]

        if len(all_centers) != 0:
            all_18_plus_centers = []
            all_45_plus_centers = []
            for center in all_centers:
                if center["name"] == "18 TO 44 YEARS":
                    all_18_plus_centers.append(center)

            for center in all_centers:
                if not center["name"] == "18 TO 44 YEARS":
                    all_45_plus_centers.append(center)

            def check_available_slots(temp_center):
                if len(temp_center) != 0:
                    for i in range(len(temp_center)):
                        if len(json_response["centers"][i]["sessions"]):
                            all_sessions = temp_center[i]["sessions"]
                            for session in all_sessions:
                                if int(session["available_capacity"]) > 0 and not (len(session["slots"]) == 0):
                                    return session['date'], True

            if execute_18_plus:
                my_values = check_available_slots(all_18_plus_centers)
                if my_values is not None:
                    available_slot_date_in_18_plus, is_slot_available_in_18_plus = my_values
            if execute_45_plus:
                my_values = check_available_slots(all_45_plus_centers)
                if my_values is not None:
                    available_slot_date_in_45_plus, is_slot_available_in_45_plus = my_values

            if not execute_18_plus:
                is_slot_available_in_18_plus = True
                available_slot_date_in_18_plus = initial_18_plus_slot_date

            if not execute_45_plus:
                is_slot_available_in_45_plus = True
                available_slot_date_in_45_plus = initial_45_plus_slot_date

        return is_slot_available_in_18_plus, available_slot_date_in_18_plus, is_slot_available_in_45_plus, available_slot_date_in_45_plus

    # Start of the Code

    firebaseConfig = {
        "apiKey": "AIzaSyAfYbZQ-ffdzf0MsJfe66glcUa5lxzctqg",
        "authDomain": "cowin-tracker-ff4c1.firebaseapp.com",
        "databaseURL": "https://cowin-tracker-ff4c1-default-rtdb.firebaseio.com",
        "projectId": "cowin-tracker-ff4c1",
        "storageBucket": "cowin-tracker-ff4c1.appspot.com",
        "messagingSenderId": "781366305325",
        "appId": "1:781366305325:web:2223effddebacdaf40cea4",
        "measurementId": "G-WW2L56PTLN",
        "serviceAccount": str(settings.BASE_DIR) + "/tracker/serviceAccountKey.json",
        # "serviceAccount": "./serviceAccountKey.json",
    }

    firebase = pyrebase.initialize_app(firebaseConfig)

    db = firebase.database()

    all_pincodes = list(db.child("Track Pin Codes").get().val().keys())

    now = datetime.now()
    tz = pytz.timezone('Asia/Kolkata')
    now.astimezone(tz)
    current_day = now.day
    current_month = now.month
    current_year = now.year

    date_today = str(current_day) + '-' + str(current_month) + '-' + str(current_year)
    date_after_one_week = str(current_day + 7) + '-' + str(current_month) + '-' + str(current_year)

    api_key = 'AAAAte0Poi0:APA91bGhEspD5CHP6kgMdcedNVi6ZOHuD-HRKJ5tU-5hkcTubozuFoHGZiQ6vWY6IBfm1jCL0gRVQiym5iCNvBNkaCyrV4IU4DS_6sM9lRxIcfqt--PP_ooaGAJ7ev8-k5gZiLya6rla'
    push_service = FCMNotification(api_key=api_key)

    for pincode in all_pincodes:
        is_18_plus_available, slot_date_for_18_plus, is_45_plus_available, slot_date_for_45_plus = call(pincode,
                                                                                                        date_today,
                                                                                                        True, "",
                                                                                                        True, "")
        should_execute_next_18 = not is_18_plus_available
        should_execute_next_45 = not is_45_plus_available

        if is_18_plus_available and is_45_plus_available:
            pass
        else:
            is_18_plus_available, slot_date_for_18_plus, is_45_plus_available, slot_date_for_45_plus = call(pincode,
                                                                                                            date_after_one_week,
                                                                                                            should_execute_next_18,
                                                                                                            slot_date_for_18_plus,
                                                                                                            should_execute_next_45,
                                                                                                            slot_date_for_45_plus)

        all_slot_tracker_modes = list(db.child("Track Pin Codes").child(pincode).get().val().keys())

        all_18_plus_subscribers = []
        all_45_plus_subscribers = []
        all_slot_subscribers = []

        for slot in all_slot_tracker_modes:

            if slot == 'is_18_plus':
                all_18_plus_subscribers = list(
                    db.child("Track Pin Codes").child(pincode).child('is_18_plus').get().val().values())

            if slot == 'is_45_plus':
                all_45_plus_subscribers = list(
                    db.child("Track Pin Codes").child(pincode).child('is_45_plus').get().val().values())

            if slot == 'is_all':
                all_slot_subscribers = list(
                    db.child("Track Pin Codes").child(pincode).child('is_all').get().val().values())

        if is_18_plus_available:
            message_title = "Hurry, 18+ Age Slots available"
            message_body = "Cowin Slots Available for Pincode " + pincode + " on " + slot_date_for_18_plus
            subscriber_list = all_18_plus_subscribers + all_slot_subscribers
            valid_subscriber_list = push_service.clean_registration_ids(subscriber_list)
            push_service.notify_multiple_devices(valid_subscriber_list, message_title=message_title,
                                                 message_body=message_body, low_priority=False)

        if is_45_plus_available:
            message_title = "Hurry, 45+ Age Slots available"
            message_body = "Cowin Slots Available for Pincode " + pincode + " on " + slot_date_for_45_plus
            subscriber_list = all_45_plus_subscribers + all_slot_subscribers
            valid_subscriber_list = push_service.clean_registration_ids(subscriber_list)
            push_service.notify_multiple_devices(valid_subscriber_list, message_title=message_title,
                                                 message_body=message_body, low_priority=False)
