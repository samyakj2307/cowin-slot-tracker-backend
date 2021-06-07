import pyrebase
from django.conf import settings
from pyfcm import FCMNotification


def cleanFunc():

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
    }

    firebase = pyrebase.initialize_app(firebaseConfig)

    db = firebase.database()

    all_pincodes = db.child("Track Pin Codes").get().val()

    
    api_key = 'AAAAte0Poi0:APA91bGhEspD5CHP6kgMdcedNVi6ZOHuD-HRKJ5tU-5hkcTubozuFoHGZiQ6vWY6IBfm1jCL0gRVQiym5iCNvBNkaCyrV4IU4DS_6sM9lRxIcfqt--PP_ooaGAJ7ev8-k5gZiLya6rla'
    push_service = FCMNotification(api_key=api_key)

    all_pincodes = list(db.child("Track Pin Codes").get().val().keys())

    print("Length of Pincode")
    print(len(all_pincodes))
    print("Length of Pincode")

    for pincode in all_pincodes:
        print(pincode)

        all_slot_tracker_modes = list(db.child("Track Pin Codes").child(pincode).child("users").get().val().keys())
        all_18_plus_subscribers = []
        all_45_plus_subscribers = []
        all_slot_subscribers = []

        x = []
        for slot in all_slot_tracker_modes:
            if slot == 'is_18_plus':
                all_18_plus_subscribers = list(
                    db.child("Track Pin Codes").child(pincode).child("users").child('is_18_plus').get().val().values())

                t = db.child("Track Pin Codes").child(pincode).child("users").child('is_18_plus').get().val()
                for key,value in t.items():
                    x.append({key:value})


            if slot == 'is_45_plus':
                all_45_plus_subscribers = list(
                    db.child("Track Pin Codes").child(pincode).child("users").child('is_45_plus').get().val().values())
                t = db.child("Track Pin Codes").child(pincode).child("users").child('is_45_plus').get().val()
                for key,value in t.items():
                    x.append({key:value})

            if slot == 'is_all':
                all_slot_subscribers = list(
                    db.child("Track Pin Codes").child(pincode).child("users").child('is_all').get().val().values())
                t = db.child("Track Pin Codes").child(pincode).child("users").child('is_all').get().val()
                for key,value in t.items():
                    x.append({key:value})

        subscriber_list = all_18_plus_subscribers + all_slot_subscribers + all_45_plus_subscribers

        valid_subscriber_list = push_service.clean_registration_ids(subscriber_list)

        for sub in subscriber_list:
            if sub not in valid_subscriber_list:
                for i in range(len(x)):
                    if list( x[i].values() )[0] == sub:
                        uid = list( x[i].keys() )[0]
                        slotType = db.child("users").child(uid).child("Pincodes").child(pincode).get().val()
                        db.child("users").child(uid).child("Pincodes").child(pincode).remove()
                        db.child("Track Pin Codes").child(pincode).child("users").child(slotType).child(uid).remove()

        print(len(subscriber_list))
        print(len(valid_subscriber_list))
