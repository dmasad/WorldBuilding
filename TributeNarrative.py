'''
Generate a narrative from TributeModel data

Overall concept: find local extrema in the time series of actor wealth; subset
extrema based on importance. The region between each two remaining extrema is
an era. Count events occuring between those points to create a narrative for
that era.

'''
from collections import defaultdict
import random
import string
import numpy as np
from extrema import rank_extrema


syllables = []
vowels = "aeiouy"
for a in vowels:
    for b in string.ascii_letters:
        if b in vowels: continue
        syllables.append(a+b)
        syllables.append(b+a)

def make_word(syl_count=3):
    word = "".join([random.choice(syllables) for i in range(syl_count)])
    if len(word) > 2 and random.random() < 0.5:
        word = word[:-1]
    return word.title()


def get_eras(data):
    #data = np.array(actor.wealth_history)
    pt_rank = rank_extrema(data)
    ranks = list(pt_rank["min"].values()) + list(pt_rank["max"].values())
    x_pts = [0, len(data)-1]
    cutoff = np.median(ranks)
    for x, count in pt_rank["max"].items():
        if count >= cutoff:
            x_pts.append(x)
    for x, count in pt_rank["min"].items():
        if count >= cutoff:
            x_pts.append(x)
    x_pts = sorted(x_pts)
    eras = [(x_pts[i], x_pts[i+1]) for i in range(len(x_pts)-1)]
    return eras

def write_era(agent, era):
    data = np.array(agent.wealth_history)
    start, end = era
    dt = end - start
    delta = data[end] - data[start]

    text = "From {} to {}, {} saw ".format(start, end, agent.name)
    # Categorize the era
    if abs(delta)/dt < np.std(np.diff(data)):
        text += "slow "
    else:
        text += "rapid "

    if delta < 0:
        text += "decline. "
    else:
        text += "growth. "

    # Get events
    event_counts = defaultdict(lambda: defaultdict(int))
    for event in agent.log:
        if era[0] < event[0] <= era[1]:
            event_type = event[1]
            event_target = event[2]
            event_counts[event_type][event_target] += 1

    war_count = len(event_counts["Led war against"])
    war_targets = list_to_words(list(event_counts["Led war against"].keys()))
    joined_wars = sum(list(event_counts["Joined war against"].values()))
    tributes = list(event_counts["Receive tribute"].keys())
    tributes_txt = list_to_words(tributes)

    if war_count + joined_wars + len(tributes) == 0:
        return text 

    if dt > 1:
        text += "In this period it"
    else:
        text += "In {} it".format(end)

    if war_count == 1:
        text += " fought a war against {}".format(war_targets)
    elif war_count > 1:
        text += " fought {} wars against {}".format(war_count, war_targets)

    if joined_wars > 0:
        if len(tributes) == 0:
            text += ", and "
        if joined_wars == 1:
            text += "joined its allies in one battle"
        else:
            text += "joined its allies in {} battles".format(joined_wars)
    if len(tributes) > 0:
        if war_count > 0 or joined_wars > 0:
            text += " and"
        text += " received tributes from {}".format(tributes_txt)
    text += "."

    return text



def list_to_words(values):
    if len(values) == 0:
        return "nobody"
    if len(values) == 1:
        return str(values[0])
    else:
        text = ", ".join(str(v) for v in values[:-1])
        text += " and {}".format(values[-1])
        return text
