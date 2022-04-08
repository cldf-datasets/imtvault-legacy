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


def process_entities(d):
    return [{"wdid": key, "label": value} for key, value in sorted(d.items(), key=lambda i: i[0])]


def run(ds):
    d = defaultdict(dict)
    for ancestor, degree, child in reader(ds.etc_dir / 'closure.csv', delimiter='\t'):
        d[child][ancestor] = True

    with jsonlib.update(
        ds.etc_dir / 'entitiestitles.json', default={}, indent=4, sort_keys=True
    ) as entitiescache:
        for ex in ds.iter_extracted_examples():
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
                ex["entities"] = process_entities(ex["entities"])
                ex["parententities"] = process_entities(ex.get("parententities", {}))
