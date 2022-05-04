"""

"""
from csvw.dsv import UnicodeWriter
from cldfbench_imtvault import Dataset
from imtvaultcommands.util.glossa import Article
from pybtex.database import parse_string


def register(parser):
    parser.add_argument('--did', default=None)


def run(args):
    ds = Dataset()
    with UnicodeWriter(ds.etc_dir / 'glossa.csv') as w:
        w.writerow(['id', 'title', 'language_name', 'language_glottocode', 'example_languages'])
        for key, entry in parse_string(ds.raw_dir.joinpath('glossa', 'glossa.bib').read_text(encoding='utf8'), 'bibtex').entries.items():
            w.writerow([key, entry.fields['title'], '', '', entry.fields.get('example_languages', '')])
