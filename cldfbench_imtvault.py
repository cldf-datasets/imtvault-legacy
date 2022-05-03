import re
import math
import pathlib
import collections

import attr
from tqdm import tqdm
from pyigt.igt import NON_OVERT_ELEMENT, LGRConformance
from cldfbench import Dataset as BaseDataset
from clldutils.misc import lazyproperty
from clldutils.path import walk
from pybtex import database
from pycldf.sources import Source, Reference
from csvw.metadata import URITemplate

from imtvaultcommands.util.latex import to_text

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


def fix_bibtex(s):
    """
    Replace macros (by just turning the macro names into strings ...)
    """
    string_pattern = re.compile(r"^@string{(.+)$")
    s = string_pattern.sub('', s)
    s = re.sub(r'\s*=\s*([a-zA-Z]+),\s*$', lambda m: ' = {' + m.groups()[0] + '},', s)
    return s


class TexDir:
    def __init__(self, p, bib, languages=None, log=None):
        self.bib = {}
        if bib.exists():
            for i, rec in enumerate(fix_bibtex(bib.read_text(encoding='utf8')).split('@')):
                if i:
                    try:
                        for k, v in database.parse_string('@' + rec, 'bibtex').entries.items():
                            self.bib[k] = (k, v)
                            for kk, vv in v.fields.items():
                                if kk.lower() == 'ids':
                                    self.bib[vv] = (k, v)
                    except Exception as e:
                        #print(bib.name, e)
                        pass
        self.languages = languages or {}
        self.dir = p
        self.file_dict = {}
        for filename in walk(self.dir, mode='files'):
            if filename.suffix != '.tex':
                continue
            try:
                s = filename.read_text(encoding='utf8')
                s = re.sub(r'\s*\\hfill\s*\[\\href{[^}]+}[^]]*]\s*$', '', s, re.MULTILINE)
                # We replace a couple of latex constructs to reduce the complexity.
                s = s.replace(r'\langinfobreak', r'\langinfo')  # Mostly a synonym.
                s = s.replace(r'{\db}{\db}{\db}', '[[[')
                s = s.replace(r'{\db}{\db}', '[[')
                s = s.replace(r'\textsc{id}:', '')
                s = s.replace(r'\glossN.', r'\glossN{}.')
                self.file_dict[filename.name] = (s, str(filename.relative_to(self.dir)))
            except UnicodeDecodeError as e:
                #print(e)
                if log:
                    log.warning("Unicode problem in %s" % filename)
                continue

    def __iter__(self):
        yield from ((self.dir / rn, fn, tex, self.languages.get(fn))
                    for fn, (tex, rn) in sorted(self.file_dict.items()))

    @staticmethod
    def get_abbreviations(tex):
        from imtvaultcommands.util.latex import to_text
        result = collections.OrderedDict()
        for line in tex.split('\n'):
            if not line.strip().startswith("%"):
                cells = line.split("&")
                if len(cells) == 2:
                    result[to_text(cells[0].strip())[0]] = to_text(cells[1].strip())[0]
        return result

    @lazyproperty
    def abbreviations(self):
        abbrfile = 'abbreviations.tex'
        res = None
        if abbrfile in self.file_dict:
            res = self.get_abbreviations(self.file_dict[abbrfile][0])
        if not res:
            for p, fn, s, _ in self:
                if fn != abbrfile:
                    try:
                        abbr = s.split("section*{Abbreviations}")[1]
                        res = self.get_abbreviations(abbr.split(r"\section")[0])
                        if res:
                            break
                    except IndexError:
                        pass
        return res

    def iter_examples(self, record, gl_by_name, unknown_lgs=None):
        from imtvaultcommands.util.extractgll import iter_gll, make_example

        seen = set()
        for filename, fn, s, filelanguage in self:
            for linfo, gll, prevline in iter_gll(s):
                ex = make_example(record, self, linfo, gll, prevline, filelanguage, gl_by_name, unknown_lgs)
                if ex:
                    if ex.ID not in seen:
                        yield ex, filename.relative_to(self.dir)
                        seen.add(ex.ID)


def delatex_source(key, entry):
    if isinstance(entry, str):
        src = Source.from_bibtex(entry)
    else:
        src = Source.from_entry(key, entry)
    for k in list(src):
        if k in ['date-added', 'date-modified']:
            del src[k]
            continue
        src[k.lower()] = to_text(src[k])[0]
        if k.lower() != k:
            del src[k]
    return src


@attr.s
class Record:
    id = attr.ib(converter=int)
    title = attr.ib()
    license = attr.ib()
    language_name = attr.ib(converter=lambda s: s or None)
    language_glottocode = attr.ib(converter=lambda s: s or None)
    status = attr.ib(
        validator=attr.validators.optional(attr.validators.in_(
            ['published', 'superseded', 'forthcoming'])),
        converter=lambda s: s or 'published')
    metalanguage = attr.ib(validator=attr.validators.in_(['eng', 'deu', 'fra', 'por', 'cmn', 'spa']))

    @property
    def cc_by(self):
        return self.license == 'CC-BY-4.0'

    @property
    def bibtex_key(self):
        return 'lsp{}'.format(self.id)

    @property
    def published(self):
        return self.status == 'published'

    def bibtex(self, d):
        def fix_bibtex(s):
            res, doi = [], False
            for line in s.split('\n'):
                if line.strip().startswith('doi'):
                    if doi:
                        continue
                    else:
                        doi = True
                if 'author' in line:
                    line = line.replace('and ', ' and ')
                res.append(line)
            return '\n'.join(res)

        return fix_bibtex(d.joinpath('{}.bib'.format(self.id)).read_text(encoding='utf8'))


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "imtvault"

    def cldf_specs(self):  # A dataset must declare all CLDF sets it creates.
        return super().cldf_specs()

    def iter_tex_dirs(self):
        filelanguages = collections.defaultdict(dict)
        for d in self.etc_dir.read_csv('texfile_titles.tsv', delimiter='\t', dicts=True):
            if d['Language']:
                filelanguages[int(d['Book_ID'])][d['Filename']] = d['Language']
        for d in self.etc_dir.read_csv('catalog.csv', dicts=True):
            rec = Record(**d)
            if rec.published and rec.cc_by:
                tex = self.raw_dir / 'raw_texfiles' / 'raw' / str(rec.id)
                if tex.exists():
                    yield rec, TexDir(tex, self.etc_dir / 'refs' / '{}.bib'.format(rec.id), filelanguages[rec.id])

    def cmd_download(self, args):
        pass

    def _schema(self, cldf):
        cldf.add_component(
            'ContributionTable',
            {
                'name': 'Examples_Count',
                'datatype': 'integer',
            },
        )
        cldf['ContributionTable', 'ID'].valueUrl = URITemplate(
            'https://langsci-press.org/catalog/book/{ID}')
        cldf.add_component(
            'LanguageTable',
            {
                'name': 'Examples_Count',
                'datatype': 'integer',
            },
            {
                'name': 'Examples_Count_Log',
                'datatype': 'number',
            },
        )
        cldf.add_component(
            'ExampleTable',
            {
                'name': 'LGR_Conformance_Level',
                'datatype': {
                    'base': 'string',
                    'format': '|'.join(re.escape(str(l)) for l in LGRConformance)}
            },
            {
                'name': 'Language_Name',
            },
            {
                'name': 'Abbreviations',
                'datatype': 'json',
            },
            {
                'name': 'Source',
                'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#source',
                'separator': ';'
            },
            {
                'name': 'Contribution_ID',
                'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#contributionReference',
            },
            # FIXME: add coorination, time, modality, polarity!?
        )
        cldf['ExampleTable', 'Analyzed_Word'].separator = '\t'
        cldf['ExampleTable', 'Gloss'].separator = '\t'

    def cmd_makecldf(self, args):
        self._schema(args.writer.cldf)
        gl_by_name = {}
        gl_by_gc = {}
        gl_by_iso = {}

        for lg in args.glottolog.api.languoids():
            gl_by_gc[lg.id] = lg
            if lg.iso:
                gl_by_iso[lg.iso] = lg
            gl_by_name[lg.name] = lg
            for _, names in lg.names.items():
                for name in names:
                    name = name.split('[')[0].strip()
                    if name not in gl_by_name:
                        gl_by_name[name] = lg
        for n, gc in LNAME_TO_GC.items():
            if gc:
                gl_by_name[n] = gl_by_gc[gc]

        args.writer.objects['LanguageTable'].append(dict(
            ID='undefined',
            Name='Undefined Language',
        ))
        langs = set()
        lgs, contribs = collections.Counter(), collections.Counter()
        for record, book in tqdm(self.iter_tex_dirs()):
            ml = gl_by_iso[record.metalanguage]
            if ml.id not in langs:
                args.writer.objects['LanguageTable'].append(dict(
                    ID=ml.id,
                    Name=ml.name,
                    Glottocode=ml.id,
                    Latitude=ml.latitude,
                    Longitude=ml.longitude,
                ))
                langs.add(ml.id)
            for i, (ex, fn) in enumerate(book.iter_examples(record, gl_by_name)):
                if i == 0:
                    src = delatex_source(None, record.bibtex(self.etc_dir / 'bibtex'))
                    args.writer.cldf.sources.add(src)
                    args.writer.objects['ContributionTable'].append(dict(
                        ID=str(record.id),
                        Name=record.title,
                        Contributor=src.get('author') or src.get('editor'),
                        Citation=str(src),
                    ))
                if not ex.Source:
                    ex.Source = [(record.bibtex_key, str(fn))]
                else:
                    nrefs = []
                    for sid, pages in ex.Source:
                        nsid = '{}_{}'.format(record.bibtex_key, sid)
                        args.writer.cldf.sources.add(delatex_source(nsid, book.bib[sid][1]))
                        nrefs.append((nsid, pages))
                    nrefs.append((record.bibtex_key, 'via:{}'.format(fn)))
                    ex.Source = nrefs
                if not ex.Language_ID:
                    ex.Language_ID = 'undefined'
                elif ex.Language_ID not in langs:
                    args.writer.objects['LanguageTable'].append(dict(
                        ID=ex.Language_ID,
                        Name=gl_by_gc[ex.Language_ID].name,
                        Glottocode=ex.Language_ID,
                        Latitude=gl_by_gc[ex.Language_ID].latitude,
                        Longitude=gl_by_gc[ex.Language_ID].longitude,
                    ))
                    langs.add(ex.Language_ID)

                args.writer.objects['ExampleTable'].append(dict(
                    ID=ex.ID,
                    Language_ID=ex.Language_ID,
                    Language_Name=ex.Language_Name,
                    Meta_Language_ID=ml.id,
                    Primary_Text=ex.Primary_Text,
                    Analyzed_Word=ex.Analyzed_Word,
                    Gloss=ex.Gloss,
                    Translated_Text=ex.Translated_Text,
                    LGR_Conformance_Level=str(ex.IGT.conformance),
                    Abbreviations=ex.IGT.gloss_abbrs if ex.IGT.conformance == LGRConformance.MORPHEME_ALIGNED else {},
                    Source=[str(Reference(k, v.replace(';', ','))) for k, v in ex.Source],
                    Comment=ex.Comment,
                    Contribution_ID=str(record.id),
                ))
                lgs.update([ex.Language_ID])
                contribs.update([str(record.id)])
            #if lgs:
            #    break

        for lg in args.writer.objects['LanguageTable']:
            if lg['ID'] != 'undefined':
                lg['Examples_Count'] = lgs.get(lg['ID'], 0)
                lg['Examples_Count_Log'] = math.log(lgs.get(lg['ID'], 1))
        for c in args.writer.objects['ContributionTable']:
            c['Examples_Count'] = contribs[c['ID']]
