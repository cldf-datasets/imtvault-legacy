from clldutils import jsonlib


def process_entities(d):
    return [{"wdid": key, "label": d[key]} for key in d]


def run(jd):
    for p in jd.glob('*json'):
        with jsonlib.update(p, sort_keys=True, indent=4, ensure_ascii=False) as json:
            for ex in json:
                if 'entities' in ex:
                    ex["entities"] = process_entities(ex["entities"])
                    ex["parententities"] = process_entities(ex.get("parententities", {}))
                ex["book_URL"] = f"https://langsci-press.org/catalog/book/{ex['book_ID']}"
                ex["language"] = None
                if ex.get("language_glottocode", "und") != "und":
                    ex["language"] = \
                        f"https://glottolog.org/resource/languoid/id/{ex['language_glottocode']}"
                srcstring = " ".join(ex["srcwordsbare"])
                ex["label"] = srcstring
