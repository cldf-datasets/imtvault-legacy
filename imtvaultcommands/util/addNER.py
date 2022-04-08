import json
import requests
import re

from clldutils import jsonlib

from .misextractions import misextractions

NUMPATTERN = re.compile("[A-Za-z][-0-9]+")  # stuff like M2-34 is not any good


def get_entities(text):
    global nercache
    """send text to online resolver and retrieve wikidataId's"""
    ner_url = "https://cloud.science-miner.com/nerd/service/disambiguate"
    if len(text.split()) < 5:  # cannot do NER on less than 5 words
        return {}
    rtext = requests.post(ner_url, json={"text": text}).text
    # parse json
    if rtext == None:
        return {}
    retrieved_entities = json.loads(rtext).get("entities", [])
    # extract names and wikidataId's
    return {
        x["wikidataId"]: x["rawName"]
        for x in retrieved_entities
        if x.get("wikidataId")
        and x["wikidataId"] not in misextractions
        and not NUMPATTERN.match(x["rawName"])
    }


def run(ds):
    with jsonlib.update(ds.etc_dir / 'nercache.json', default={}) as nercache:
        for ex in ds.iter_extracted_examples():
            if ex["trs"] not in nercache:
                nercache[ex["trs"]] = get_entities(ex['trs'])
            ex["entities"] =  nercache[ex['trs']]
