"""

"""
import re
import urllib.request

import attr
from csvw.dsv import UnicodeWriter
from bs4 import BeautifulSoup

from .util.lsp import Record
from cldfbench_imtvault import Dataset

BOOK_URL = re.compile(r'https://langsci-press.org/catalog/book/([0-9]+)')

# FIXME: 284: Forthcoming!
def run(args):
    ds = Dataset()
    url = "https://langsci-press.org/catalog"
    html = BeautifulSoup(urllib.request.urlopen(url).read().decode('utf8'))
    recs = []
    for title in html.find_all('h2', class_='title'):
        link = title.find('a', href=True)
        if link:
            m = BOOK_URL.fullmatch(link['href'])
            if m:
                recs.append(Record(m.groups()[0], link.text.strip()))

    with UnicodeWriter(ds.etc_dir / 'catalog.csv') as w:
        w.writerow([f.name for f in attr.fields(Record)])
        for r in sorted(recs, key=lambda r: r.id):
            w.writerow(attr.astuple(r))
