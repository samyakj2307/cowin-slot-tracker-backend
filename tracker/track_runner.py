from datetime import datetime

import pyrebase
import pytz
import requests
from celery import shared_task
from django.conf import settings

# from fake_useragent import UserAgent
from pyfcm import FCMNotification
import time
from calendar import monthrange


@shared_task(name="tracker")
def my_cowin_runner():
    def call(
        pin_code,
        date,
        execute_18_plus,
        initial_18_plus_slot_date,
        execute_45_plus,
        initial_45_plus_slot_date,
    ):

        url = f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByPin?pincode={pin_code}&date={date}"
        # ua = UserAgent()

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"
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

        all_18_plus_sessions = []
        all_45_plus_sessions = []

        if len(all_centers) != 0:
            for center in all_centers:
                all_sessions = center["sessions"]
                for session in all_sessions:
                    if session["min_age_limit"] == 18:
                        all_18_plus_sessions.append(session)
                    elif session["min_age_limit"] == 45:
                        all_45_plus_sessions.append(session)

        def check_available_slots(temp_sessions):
            if len(temp_sessions) != 0:
                for session in temp_sessions:
                    if int(session["available_capacity"]) > 0 and not (
                        len(session["slots"]) == 0
                    ):
                        return (session["date"], True)

        if execute_18_plus:
            my_values = check_available_slots(all_18_plus_sessions)
            if my_values is not None:
                available_slot_date_in_18_plus, is_slot_available_in_18_plus = my_values
        elif not execute_18_plus:
            is_slot_available_in_18_plus = True
            available_slot_date_in_18_plus = initial_18_plus_slot_date

        if execute_45_plus:
            my_values = check_available_slots(all_45_plus_sessions)
            if my_values is not None:
                available_slot_date_in_45_plus, is_slot_available_in_45_plus = my_values
        elif not execute_45_plus:
            is_slot_available_in_45_plus = True
            available_slot_date_in_45_plus = initial_45_plus_slot_date

        return (
            is_slot_available_in_18_plus,
            available_slot_date_in_18_plus,
            is_slot_available_in_45_plus,
            available_slot_date_in_45_plus,
        )

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

    if db.child("Track Pin Codes").get().val() != None:

        all_pincodes = list(db.child("Track Pin Codes").get().val().keys())

        database_api_call_counter = (
            db.child("api_call_counter_details").child("api_call_counter").get().val()
        )
        current_api_call_counter = 0
        init_timestamp = time.time()
        last_used_timestamp = (
            db.child("api_call_counter_details").child("timestamp").get().val()
        )

        if (
            init_timestamp - last_used_timestamp
        ) < 310 and database_api_call_counter > 90:
            sleeping_time = 310 - (init_timestamp - last_used_timestamp)
            print("Sleeping for" + sleeping_time + "seconds in outer loop")
            time.sleep(sleeping_time)
            database_api_call_counter = 0
        elif (init_timestamp - last_used_timestamp) > 310:
            database_api_call_counter = 0

        now = datetime.now()
        tz = pytz.timezone("Asia/Kolkata")
        now.astimezone(tz)
        print(now)
        current_day = now.day
        current_month = now.month
        current_year = now.year
        current_year = 21

        date_today = f"{current_day}-{current_month}-{current_year}"
        print(date_today)

        days_in_current_month = monthrange(current_year, current_month)[1]

        after_7_days_day = current_day + 7
        after_7_day_mod = (after_7_days_day) % days_in_current_month
        after_7_days_month = current_month

        if after_7_day_mod != 0 and after_7_day_mod < current_day:
            after_7_days_day = after_7_day_mod
            after_7_days_month += 1

        date_after_one_week = f"{after_7_days_day}-{after_7_days_month}-{current_year}"
        print(date_after_one_week)

        api_key = "AAAAte0Poi0:APA91bGhEspD5CHP6kgMdcedNVi6ZOHuD-HRKJ5tU-5hkcTubozuFoHGZiQ6vWY6IBfm1jCL0gRVQiym5iCNvBNkaCyrV4IU4DS_6sM9lRxIcfqt--PP_ooaGAJ7ev8-k5gZiLya6rla"
        push_service = FCMNotification(api_key=api_key)

        print(all_pincodes)
        print(len(all_pincodes))
        for pincode in all_pincodes:
            print(pincode)
            if current_api_call_counter + database_api_call_counter >= 98:
                print("Sleeping for five minutes in inner loop")
                time.sleep(300)
                current_api_call_counter = 0

            print("First Call")
            (
                is_18_plus_available,
                slot_date_for_18_plus,
                is_45_plus_available,
                slot_date_for_45_plus,
            ) = call(pincode, date_today, True, "", True, "")
            current_api_call_counter += 1
            should_execute_next_18 = not is_18_plus_available
            should_execute_next_45 = not is_45_plus_available

            if is_18_plus_available and is_45_plus_available:
                pass
            else:
                print("Second Call")
                (
                    is_18_plus_available,
                    slot_date_for_18_plus,
                    is_45_plus_available,
                    slot_date_for_45_plus,
                ) = call(
                    pincode,
                    date_after_one_week,
                    should_execute_next_18,
                    slot_date_for_18_plus,
                    should_execute_next_45,
                    slot_date_for_45_plus,
                )
                current_api_call_counter += 1

            all_slot_tracker_modes = list(
                db.child("Track Pin Codes")
                .child(pincode)
                .child("users")
                .get()
                .val()
                .keys()
            )

            all_18_plus_subscribers = []
            all_45_plus_subscribers = []
            all_slot_subscribers = []

            for slot in all_slot_tracker_modes:

                if slot == "is_18_plus":
                    all_18_plus_subscribers = list(
                        db.child("Track Pin Codes")
                        .child(pincode)
                        .child("users")
                        .child("is_18_plus")
                        .get()
                        .val()
                        .values()
                    )

                if slot == "is_45_plus":
                    all_45_plus_subscribers = list(
                        db.child("Track Pin Codes")
                        .child(pincode)
                        .child("users")
                        .child("is_45_plus")
                        .get()
                        .val()
                        .values()
                    )

                if slot == "is_all":
                    all_slot_subscribers = list(
                        db.child("Track Pin Codes")
                        .child(pincode)
                        .child("users")
                        .child("is_all")
                        .get()
                        .val()
                        .values()
                    )

            if is_18_plus_available:

                data_message = {
                    "slot_type": "18+",
                    "date": slot_date_for_18_plus,
                    "pincode": pincode,
                }

                message_title = "Hurry, 18+ Age Slots available"
                message_body = (
                    "Cowin Slots Available for Pincode "
                    + pincode
                    + " on "
                    + slot_date_for_18_plus
                )
                subscriber_list = all_18_plus_subscribers + all_slot_subscribers

                # valid_subscriber_list = push_service.clean_registration_ids(subscriber_list)

                push_service.notify_multiple_devices(
                    subscriber_list,
                    message_title=message_title,
                    message_body=message_body,
                    low_priority=False,
                    data_message=data_message,
                )

            if is_45_plus_available:
                data_message = {
                    "slot_type": "45+",
                    "date": slot_date_for_45_plus,
                    "pincode": pincode,
                }

                message_title = "Hurry, 45+ Age Slots available"
                message_body = (
                    "Cowin Slots Available for Pincode "
                    + pincode
                    + " on "
                    + slot_date_for_45_plus
                )
                subscriber_list = all_45_plus_subscribers + all_slot_subscribers
                # print(subscriber_list)
                # valid_subscriber_list = push_service.clean_registration_ids(subscriber_list)
                # print(valid_subscriber_list)
                push_service.notify_multiple_devices(
                    subscriber_list,
                    message_title=message_title,
                    message_body=message_body,
                    low_priority=False,
                    data_message=data_message,
                )

            print("Next Pincode")

        db.child("api_call_counter_details").child("api_call_counter").set(
            current_api_call_counter
        )
        db.child("api_call_counter_details").child("timestamp").set(init_timestamp)

    else:
        print("No Pincodes to Track")
