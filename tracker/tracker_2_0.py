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

api_key = "AAAAte0Poi0:APA91bGhEspD5CHP6kgMdcedNVi6ZOHuD-HRKJ5tU-5hkcTubozuFoHGZiQ6vWY6IBfm1jCL0gRVQiym5iCNvBNkaCyrV4IU4DS_6sM9lRxIcfqt--PP_ooaGAJ7ev8-k5gZiLya6rla"
push_service = FCMNotification(api_key=api_key)


def get_data_from_api(pincode, date):
    ###### Get Center Data #########
    print(f'Getting Data for {pincode}')
    url = f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByPin?pincode={pincode}&date={date}"
    # ua = UserAgent()

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    print(f'Json response Code {response.status_code}')
    response.content.decode()
    return response


def classify_sessions(center):
    ############# Seperating 18+ and 45+ Sessions ###################
    all_sessions = center["sessions"]
    all_18_plus_sessions = []
    all_45_plus_sessions = []

    for session in all_sessions:
        session["center_id"] = center["center_id"]
        if session["available_capacity"] > 0:
            if session["min_age_limit"] == 18:
                all_18_plus_sessions.append(session)
                if "allow_all_age" in session.keys() and session["allow_all_age"]:
                    all_45_plus_sessions.append(session)
            elif session["min_age_limit"] == 45:
                all_45_plus_sessions.append(session)

    return all_18_plus_sessions, all_45_plus_sessions


def get_seperate_centers(all_centers):
    ######## Seperating Free and Paid Centers ###########
    all_free_centers = []
    all_paid_centers = []

    if len(all_centers) != 0:
        for center in all_centers:
            if center["fee_type"] == "Free":
                all_free_centers.append(center)
            elif center["fee_type"] == "Paid":
                all_paid_centers.append(center)
    return all_free_centers, all_paid_centers


def get_all_subscribers(fee_type, pincode, all_age_type, db):
    all_18_plus_subscribers = []
    all_45_plus_subscribers = []
    for age_type in all_age_type:
        if age_type == "is_18_plus":
            all_18_plus_subscribers = list(
                db.child("Track_Pin_Codes_2_0")
                    .child(pincode)
                    .child(fee_type)
                    .child("is_18_plus")
                    .get()
                    .val()
                    .values()
            )
        elif age_type == "is_45_plus":
            all_45_plus_subscribers = list(
                db.child("Track_Pin_Codes_2_0")
                    .child(pincode)
                    .child(fee_type)
                    .child("is_45_plus")
                    .get()
                    .val()
                    .values()
            )

    return all_18_plus_subscribers, all_45_plus_subscribers


def send_message_to_18_plus(date, pincode, capacity, all_18_plus_subscribers, session_id, center_id, fee_type):
    print("18+ Available")
    data_message = {
        "slot_type": "18+",
        "date": date,
        "pincode": pincode,
        "available_capacity": capacity,
        "center_id": center_id,
        "session_id": session_id,
    }

    message_title = f'Hurry, 18+ Age Slots({fee_type}) available'
    message_body = f'{capacity} Slots Available for Pincode {pincode} on {date}'
    subscriber_list = all_18_plus_subscribers

    # valid_subscriber_list = push_service.clean_registration_ids(subscriber_list)

    push_service.notify_multiple_devices(
        subscriber_list,
        message_title=message_title,
        message_body=message_body,
        low_priority=False,
        data_message=data_message,
    )


def send_message_to_45_plus(date, pincode, capacity, all_45_plus_subscribers, session_id, center_id, fee_type):
    print("45+ Available")
    data_message = {
        "slot_type": "45+",
        "date": date,
        "pincode": pincode,
        "available_capacity": capacity,
        "center_id": center_id,
        "session_id": session_id,
    }

    message_title = f'Hurry, 45+ Age Slots({fee_type}) available'
    message_body = f'{capacity} Slots Available for Pincode {pincode} on {date}'
    subscriber_list = all_45_plus_subscribers

    # valid_subscriber_list = push_service.clean_registration_ids(subscriber_list)

    push_service.notify_multiple_devices(
        subscriber_list,
        message_title=message_title,
        message_body=message_body,
        low_priority=False,
        data_message=data_message,
    )


@shared_task(name="tracker_2_0")
def my_cowin_runner():
    firebase_config = {
        "apiKey": "AIzaSyAfYbZQ-ffdzf0MsJfe66glcUa5lxzctqg",
        "authDomain": "cowin-tracker-ff4c1.firebaseapp.com",
        "databaseURL": "https://cowin-tracker-ff4c1-default-rtdb.firebaseio.com",
        "projectId": "cowin-tracker-ff4c1",
        "storageBucket": "cowin-tracker-ff4c1.appspot.com",
        "messagingSenderId": "781366305325",
        "appId": "1:781366305325:web:2223effddebacdaf40cea4",
        "measurementId": "G-WW2L56PTLN",
        "serviceAccount": str(settings.BASE_DIR) + "/tracker/serviceAccountKey.json",
    }

    firebase = pyrebase.initialize_app(firebase_config)

    db = firebase.database()

    if db.child("Track_Pin_Codes_2_0").get().val() is not None:
        all_pincodes = list(db.child("Track_Pin_Codes_2_0").get().val().keys())

        database_api_call_counter = db.child("api_call_counter_details_2_0").child("api_call_counter").get().val()

        current_api_call_counter = 0
        init_timestamp = time.time()
        last_used_timestamp = (
            db.child("api_call_counter_details_2_0").child("timestamp").get().val()
        )

        if (init_timestamp - last_used_timestamp) < 310 and database_api_call_counter > 90:
            sleeping_time = 310 - (init_timestamp - last_used_timestamp)
            print("Sleeping for" + sleeping_time + "seconds in outer loop")
            time.sleep(sleeping_time)
            database_api_call_counter = 0
        elif (init_timestamp - last_used_timestamp) > 310:
            database_api_call_counter = 0

        now = datetime.now()
        tz = pytz.timezone("Asia/Kolkata")
        now.astimezone(tz)
        current_day = now.day
        current_month = now.month
        # current_year = now.year
        current_year = 21

        date_today = f"{current_day}-{current_month}-{current_year}"
        print(f'Date Today: {date_today}')

        # days_in_current_month = monthrange(current_year, current_month)[1]
        #
        # after_7_days_day = current_day + 7
        # after_7_day_mod = after_7_days_day % days_in_current_month
        # after_7_days_month = current_month

        # if after_7_day_mod != 0 and after_7_day_mod < current_day:
        #     after_7_days_day = after_7_day_mod
        #     after_7_days_month += 1

        # date_after_one_week = f"{after_7_days_day}-{after_7_days_month}-{current_year}"

        for pincode in all_pincodes:
            if current_api_call_counter + database_api_call_counter >= 98:
                print("Sleeping for five minutes in inner loop")
                time.sleep(300)
                current_api_call_counter = 0

            response = get_data_from_api(pincode, date_today)
            current_api_call_counter += 1
            json_response = response.json()
            all_centers = json_response["centers"]

            if all_centers is not None:
                all_free_centers, all_paid_centers = get_seperate_centers(all_centers)

                all_free_18_plus_sessions = []
                all_free_45_plus_sessions = []
                all_paid_18_plus_sessions = []
                all_paid_45_plus_sessions = []

                for center in all_free_centers:
                    session_18_plus, session_45_plus = classify_sessions(center)
                    if len(session_18_plus) > 0:
                        all_free_18_plus_sessions += session_18_plus
                    if len(session_45_plus) > 0:
                        all_free_45_plus_sessions += session_45_plus

                for center in all_paid_centers:
                    session_18_plus, session_45_plus = classify_sessions(center)
                    if len(session_18_plus) > 0:
                        all_paid_18_plus_sessions += session_18_plus
                    if len(session_45_plus) > 0:
                        all_paid_45_plus_sessions += session_45_plus

                all_fee_type = list(db.child("Track_Pin_Codes_2_0").child(pincode).get().val().keys())

                if "Free" in all_fee_type and (
                        len(all_free_18_plus_sessions) > 0 or len(all_free_45_plus_sessions) > 0):
                    all_free_age_type = list(
                        db.child("Track_Pin_Codes_2_0")
                            .child(pincode)
                            .child("Free")
                            .get()
                            .val()
                            .keys())

                    all_free_18_plus_subscribers, all_free_45_plus_subscribers = get_all_subscribers("Free",
                                                                                                     pincode,
                                                                                                     all_free_age_type,
                                                                                                     db)

                    if "is_18_plus" in all_free_age_type and len(all_free_18_plus_sessions) > 0:
                        session = all_free_18_plus_sessions[0]
                        date = session["date"]
                        capacity = session["available_capacity"]
                        session_id = session["session_id"]
                        center_id = session["center_id"]
                        send_message_to_18_plus(date, pincode, capacity, all_free_18_plus_subscribers, session_id,
                                                center_id, "Free")

                    if "is_45_plus" in all_free_age_type and len(all_free_45_plus_sessions) > 0:
                        session = all_free_45_plus_sessions[0]
                        date = session["date"]
                        capacity = session["available_capacity"]
                        session_id = session["session_id"]
                        center_id = session["center_id"]
                        send_message_to_45_plus(date, pincode, capacity, all_free_45_plus_subscribers, session_id,
                                                center_id, "Free")

                elif "Paid" in all_fee_type and (
                        len(all_paid_18_plus_sessions) > 0 or len(all_paid_45_plus_sessions) > 0):
                    all_paid_age_type = list(
                        db.child("Track_Pin_Codes_2_0")
                            .child(pincode)
                            .child("Paid")
                            .get()
                            .val()
                            .keys())

                    all_paid_18_plus_subscribers, all_paid_45_plus_subscribers = get_all_subscribers("Paid",
                                                                                                     pincode,
                                                                                                     all_paid_age_type,
                                                                                                     db)

                    if "is_18_plus" in all_paid_age_type and len(all_paid_18_plus_sessions) > 0:
                        session = all_paid_18_plus_sessions[0]
                        date = session["date"]
                        capacity = session["available_capacity"]
                        session_id = session["session_id"]
                        center_id = session["center_id"]
                        send_message_to_18_plus(date, pincode, capacity, all_paid_18_plus_subscribers, session_id,
                                                center_id, "Paid")

                    if "is_45_plus" in all_paid_age_type and len(all_paid_45_plus_sessions) > 0:
                        session = all_paid_45_plus_sessions[0]
                        date = session["date"]
                        capacity = session["available_capacity"]
                        session_id = session["session_id"]
                        center_id = session["center_id"]
                        send_message_to_45_plus(date, pincode, capacity, all_paid_45_plus_subscribers, session_id,
                                                center_id, "Paid")

        db.child("api_call_counter_details_2_0").child("api_call_counter").set(
            current_api_call_counter
        )
        db.child("api_call_counter_details_2_0").child("timestamp").set(init_timestamp)

    else:
        print("No Pincodes to Track")
