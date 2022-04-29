"""

"""
import random

from cldfbench.cli_util import add_catalog_spec
from cldfbench_imtvault import Dataset

LNAME_TO_GC = {
    'Logoori': 'logo1258',
    'Līkpākpáln': 'konk1269',
    'Totoró Namtrik': 'toto1306',
    'Jóola Fóoñi': 'jola1263',
    'Mojeño Trinitario': 'trin1274',
    'Bùlì': 'buli1254',
    'Sereer-Siin': 'sere1260', # 45
    'Fròʔò': 'tagw1240', # 45
    'Siwi Berber': 'siwi1239', # 41
    'Hoocąk': 'hoch1243', # 40
    'Veraa': 'vera1241', # 39
    'Early Vedic': '', # 36
    'Greek, Attic': 'atti1240', # 34
    'Late Modern Swedish': '', # 30
    'Sembiran Balinese': '', # 24
    'Beirut/Damascus': '', # 24
    'Tsotsil': 'tzot1259', # 23
    'Kakataibo': 'cash1251', # 23
    'Bantu': '', # 22
    'North Sámi': '', # 22
    'Nganasan  (Avam)': 'avam1236', # 21
    'Lycopolitan Coptic': 'lyco1237', # 20
    'inglês': 'stan1293', # 18
    'Greek, Classical|(': 'anci1242', # 18
    'Greek, Homeric': 'anci1242', # 17
    'Greek, Homeric|(': 'anci1242', # 17
    'Greek, Cypriot': 'cypr1249', # 17
    "K'abeena": 'alab1254', # 16
    'francês': 'stan1290', # 16
    'Luragooli': 'logo1258', # 15
    'Rhonga': 'rong1268', # 15
    'Sino-Japanese': '', # 14
    'Hellenic': '', # 14
    'Slavonic': 'chur1257', # 13
    'Greek, Doric': 'dori1248', # 13
    'Yixing Chinese': '', # 13
    'Standard German': 'stan1295', # 13
    'Allemand': 'stan1295', # 12
    'Ioway, Otoe-Missouria': 'iowa1245', # 12
    'Tanti Dargwa': '', # 12

    'Singapore Malay': 'mala1479',  # 42
    'Early Modern Japanese': 'nucl1643',  # 23
    'Gulf Pidgin Arabic': 'pidg1248',  # 4
    'Nêlêmwa': 'kuma1276',  # 4
    'Övdalian': 'elfd1234',  # 15
    'Present-day Swedish': 'stan1279',  # 14
    'Älvdalen (Os)': 'elfd1234',  # 11
    'Sollerön (Os)': 'soll1234',  # 6
    'Orsa (Os)': 'orsa1234',  # 6
    'Nama-Damara': 'dama1270',  # 5
    'Nǀuuki': 'nuuu1241',  # 5
    r'\LangTurk': 'nucl1301',  # 5
    r'\LangTok': 'tokp1240',  # 4
    r'\LangVed': 'sans1269',  # 4
    r'\LangJap': 'nucl1643',  # 4
    r'\LangQue': 'quec1387',  #
    r'\LangMang': 'mang1381',  # 3
    r'\LangMand': 'mand1415',  # 3
    'Standard Greek': 'mode1248',  # 3
    'Överkalix (Kx)': 'arch1246',  # 3
    'Donno Sɔ': 'donn1239',  # 3
    'Ḥassāniyya': 'hass1238',  # 3
}
"""
lg 19
Beirut/Damascus 14
Pidgin Madame 7
Juba 6
 6
Old Bengali 5
LANGUAGE 4
Early Written Medieval Swedish 3
Skelletmål 3
Sason 3
Cilician 3
Old Rajasthani 3
\langHC 3
\langST 3
Tegelen Dutch 3
Early Modern japanese 2
Aanaar Saami 2
West ǃXõo 2
East ǃXõo 2
Upplandic (17\textsuperscript{th 2
Nederkalix (Kx) 2
Written Medieval Swedish 2
Lulemål 2
Älvdalen (Os)  2
Ore (Os) 2
Västra Ämtervik (Vm) 2
"""


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
            exs = []
            for ex, fn in book.iter_examples(record, gl_by_name):
                exs.append((ex, fn))
                continue
                s = str(ex.IGT)
                print(ds.raw_dir / 'raw_texfiles' / 'raw' / str(record.id) / fn)
                print(s)
                print('---')
            #print(record.id, cnt, record.title if cnt == 0 else '')
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
