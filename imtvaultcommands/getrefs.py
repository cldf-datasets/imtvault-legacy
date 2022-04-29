"""

"""
import requests

from cldfbench_imtvault import Dataset

URL = "https://raw.githubusercontent.com/langsci/{}/master/localbibliography.bib"


def run(args):
    ds = Dataset()
    for rec, td in ds.iter_tex_dirs():
        res = requests.get(URL.format(rec.id))
        if res.status_code == 200:
            ds.etc_dir.joinpath('refs', '{}.bib'.format(rec.id)).write_text(res.text, encoding='utf8')
