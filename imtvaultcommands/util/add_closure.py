from collections import defaultdict

import wptools
from clldutils import jsonlib
from csvw.dsv import reader

from .wikidata_exclude import excludelist
from .misextractions import misextractions


def get_title(wikidata_ID, entitiescache):
    try:
        title = entitiescache[wikidata_ID]
    except KeyError:
        try:
            title = (
                wptools.page(wikibase=wikidata_ID, silent=True)
                .get_wikidata()
                .data.get("title", "no title")
            )
        except:  # API KeyError
            title = None
        entitiescache[wikidata_ID] = title
    return title


def run(jd, etc):
    d = defaultdict(dict)
    for ancestor, degree, child in reader(etc / 'closure.csv', delimiter='\t'):
        d[child][ancestor] = True

    with jsonlib.update(etc / 'entitiestitles.json', default={}, indent=4, sort_keys=True) as entitiescache:
        for p in jd.glob('*json'):
            with jsonlib.update(p, sort_keys=True, indent=4, ensure_ascii=False) as json:
                for ex in json:
                    if 'entities' in ex:
                        entities = ex.get("entities", [])
                        parents = []
                        for entity in entities:
                            if entity in misextractions:
                                continue
                            parents += list(d[entity].keys())
                        parents = {
                            parent: get_title(parent, entitiescache)
                            for parent in parents
                            if parent not in entities and parent not in excludelist
                        }
                        if parents != {}:
                            ex["parententities"] = parents
