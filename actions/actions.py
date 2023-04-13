# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


from dis import dis
from typing import Any, Text, Dict, List, Union, Optional
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, FollowupAction

import csv
import random

data_file = 'data.csv'

MIN_NECESSARY_ENTRIES = 4

userLogHeader = []
userLog = []
last14Days = []
scoreTotal = 0

resources = []

resource_files = {
    'cbt': 'resources_cbt.csv',
    'local_support_groups': 'resources_local_support_groups.csv',
    'off_campus': 'resources_off_campus.csv',
    'on_campus': 'resources_on_campus.csv',
    'online_forums': 'resources_online_forums.csv'
}

on_off_campus_preference = None
online_in_person_preference = None


def load_resources(resource_type):
    global resources
    resources = []

    with open(resource_files[resource_type], 'r') as file:
        csvreader = csv.reader(file)
        next(csvreader)

        for row in csvreader:
            if len(row[0]):
                resources.append(row)


def get_resources_string(resource_type):
    result = ""

    if resource_type == 'cbt':
        result += "I would recommend CBT as a highly effective therapy for managing and reducing symptoms of anxiety. Here are some suggestions that might help you:\n"

    elif resource_type == 'local_support_groups':
        result += "Here are some local support group suggestions that might help you:\n"

    elif resource_type == 'online_forums':
        result += "Here are some online forum suggestions that might help you:\n"

    elif resource_type == 'off_campus':
        result += "Here are some off-campus mental health services that you can use:\n"

    elif resource_type == 'on_campus':
        result += "Here are some on-campus mental health support options that you can try:\n"

    for resource in resources:
        result += "[%s](%s)\n" % (resource[0], resource[1])

    return result


def update_user_log():
    global userLogHeader
    global last14Days
    global userLog

    userLogHeader = []
    userLog = []
    last14Days = []

    with open(data_file, 'r') as file:
        csvreader = csv.reader(file)
        userLogHeader = next(csvreader)

        for row in csvreader:
            if (len(row[0])):
                userLog.append(row)

    last14Days = list(filter(lambda log: datetime.strptime(
        log[0], "%Y-%m-%d") >= datetime.today() - timedelta(days=14), userLog))


update_user_log()


print(userLogHeader)
print(userLog)


def calculate_score():
    update_user_log()
    global scoreTotal
    scoreTotal = 0

    for idx in range(1, 8):
        symptomLog = list(map(lambda log: log[idx], last14Days))
        print(symptomLog)
        daysWithSymptom = symptomLog.count("1")
        frequencyRatio = daysWithSymptom / 14
        print(idx)
        print(frequencyRatio)
        scoreTotal += 3 if frequencyRatio > 0.75 \
            else 2 if frequencyRatio > 0.5 \
            else 1 if frequencyRatio > 0.25 \
            else 0


calculate_score()


symptomIndicesCsv = {
    'nervous_anxious': 1,
    'cant_stop_worrying': 2,
    'multiple_worries': 3,
    'trouble_relaxing': 4,
    'restless': 5,
    'annoyed_irritable': 6,
    'afraid_bad_things': 7
}

sorryMessages = [
    "I'm sorry to hear that you're struggling with this symptom.",
    "It must be really tough to deal with those feelings.",
    "I feel for you and wish I could make it better.",
    "I can only imagine how overwhelming it must be to deal with anxiety symptoms.",
    "I'm here for you and want to support you in any way that I can.",
    "You're not alone in this, and I'm here to help you through it.",
    "Please know that I care about you and am here to listen whenever you need to talk.",
    "You're a strong person, and I have faith that you'll get through this.",
    "It's not easy to cope with that feeling, and I admire your courage in facing it.",
    "I'm sorry that you have to go through this.",
    "You don't have to face this alone - I'm here to walk with you every step of the way.",
    "It's okay to not be okay sometimes, and I'm here to support you during those times.",
    "I'm sorry that you're feeling this way, and I hope that you find comfort in knowing that I care about you."
]


class log_symptom(Action):

    def name(self) -> Text:
        return "log_symptom"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        currentDate = str(date.today())
        currentDateLogIndices = [idx for idx, log in enumerate(
            userLog) if log[0] == currentDate]

        symptom = tracker.latest_message['intent'].get('name')
        symptomIndex = symptomIndicesCsv[symptom]

        if len(currentDateLogIndices) == 0:
            newLog = [''] * 8
            newLog[0] = currentDate
            newLog[symptomIndex] = '1'
            userLog.append(newLog)
        else:
            currentDateLog = userLog[currentDateLogIndices[0]]
            # currentDateLog[symptomIndex] = int(
            #     currentDateLog[symptomIndex]) + 1
            currentDateLog[symptomIndex] = '1'

        print(userLog)

        with open(data_file, 'w') as f:
            # using csv.writer method from CSV package
            write = csv.writer(f)
            write.writerow(userLogHeader)
            write.writerows(userLog)

        print("SYMPTOM LOGGED")
        print(symptom)
        calculate_score()

        dispatcher.utter_message(
            text="%s Are you feeling anything else?" % random.choice(sorryMessages))

        return [FollowupAction("action_listen")]


class get_score(Action):

    def name(self) -> Text:
        return "get_score"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        if len(last14Days) < MIN_NECESSARY_ENTRIES:
            dispatcher.utter_message(
                text="As far as it goes, we do not have enough entries yet to determine you have anxiety. Keep logging and soon we will know better.")

            return [FollowupAction("action_listen")]

        else:
            dispatcher.utter_message(
                text="Based on your logs from the last 14 days, your total score is %d." % scoreTotal)

            if scoreTotal > 15:
                dispatcher.utter_message(
                    text="This means you may have severe anxiety.")
            elif scoreTotal > 10:
                dispatcher.utter_message(
                    text="This means you may have moderately severe anxiety.")
            elif scoreTotal > 5:
                dispatcher.utter_message(
                    text="This means you may have moderate anxiety.")
            else:
                dispatcher.utter_message(
                    text="This means you may have mild anxiety.")

        return [FollowupAction("share_resources")]


class set_preference(Action):

    def name(self) -> Text:
        return "set_preference"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        calculate_score()

        global on_off_campus_preference
        global online_in_person_preference

        suggested_resource = ''

        preference = tracker.latest_message['intent'].get('name')

        if preference == "on_campus" or preference == "off_campus":
            on_off_campus_preference = preference

        if preference == "in_person" or preference == "online":
            online_in_person_preference = preference

        return [FollowupAction("share_resources")]


class share_resources(Action):

    def name(self) -> Text:
        return "share_resources"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        calculate_score()

        suggested_resource = ''
        global on_off_campus_preference
        global online_in_person_preference

        if scoreTotal > 10:
            if on_off_campus_preference:
                suggested_resource = on_off_campus_preference
            else:
                # dispatcher.utter_message(
                #     text="I would suggest that you get in touch with a professional therapist.")
                # return [FollowupAction("seeing_therapist_form")]
                dispatcher.utter_message(
                    text="I would suggest that you get in touch with a professional therapist. Would you prefer on-campus or off-campus support?")
                return [FollowupAction("action_listen")]
        elif scoreTotal > 5:
            if online_in_person_preference:
                suggested_resource = "online_forums" if online_in_person_preference == 'online' else "local_support_groups"
            else:
                dispatcher.utter_message(text="I would recommend exploring online forums or local support groups about anxiety as they can provide a safe space to connect with others, share experiences, and access valuable resources and information. Would you prefer learning more about online forums or local support groups?")
                return [FollowupAction("action_listen")]
        else:
            suggested_resource = 'cbt'

        load_resources(suggested_resource)

        dispatcher.utter_message(
            text=get_resources_string(suggested_resource))

        dispatcher.utter_message(text="Did that help?")

        return [FollowupAction("action_listen")]
