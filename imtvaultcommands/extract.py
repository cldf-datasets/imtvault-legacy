"""

"""
from cldfbench.cli_util import add_catalog_spec
from cldfbench_imtvault import Dataset

from .util.extractgll import langsciextract
from .util import addNER
from .util import add_closure

LNAME_TO_GC = {
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


def run(args):
    ds = Dataset()
    gl_by_name = {}
    gl_by_gc = {}
    for lg in args.glottolog.api.languoids():
        gl_by_gc[lg.id] = lg
        gl_by_name[lg.name] = lg
        for _, names in lg.names.items():
            for name in names:
                name = name.split('[')[0].strip()
                if name not in gl_by_name:
                    gl_by_name[name] = lg
    for n, gc in LNAME_TO_GC.items():
        gl_by_name[n] = gl_by_gc[gc]
    langsciextract(ds, gl_by_name)
    addNER.run(ds)
    add_closure.run(ds)
