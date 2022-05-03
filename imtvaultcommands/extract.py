"""

"""
import random

from cldfbench.cli_util import add_catalog_spec
from cldfbench_imtvault import Dataset, LNAME_TO_GC


def register(parser):
    add_catalog_spec(parser, 'glottolog')
    parser.add_argument('-b', '--book-id', default=None)
    parser.add_argument('--no-glottolog', action='store_true', default=False)
    parser.add_argument('-s', '--sample', type=int, default=0)


def run(args):
    ds = Dataset()
    gl_by_name = {}
    gl_by_gc = {}

    if not args.no_glottolog:
        for lg in args.glottolog.api.languoids():
            gl_by_gc[lg.id] = lg
            gl_by_name[lg.name] = lg
            for _, names in lg.names.items():
                for name in names:
                    name = name.split('[')[0].strip()
                    if name not in gl_by_name:
                        gl_by_name[name] = lg
        for n, gc in LNAME_TO_GC.items():
            if gc:
                gl_by_name[n] = gl_by_gc[gc]

    all = 0
    for record, book in ds.iter_tex_dirs():
        if not args.book_id or (args.book_id == str(record.id)):
            exs = list(book.iter_examples(record, gl_by_name))

            if args.sample:
                for ex, fn in (random.sample(exs, args.sample) if len(exs) > args.sample else exs):
                    s = str(ex.IGT)
                    print(ds.raw_dir / 'raw_texfiles' / 'raw' / str(record.id) / fn)
                    print(s)
                    print('---')
            else:
                print('{}: {}'.format(record.id, len(exs)))
            all += len(exs)
    print(all)
