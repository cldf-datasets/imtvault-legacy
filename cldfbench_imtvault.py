import re
import math
import pathlib
import collections
import urllib.request

from tqdm import tqdm
from pyigt import IGT
from pyigt.igt import NON_OVERT_ELEMENT, LGRConformance
from clldutils.jsonlib import load
from cldfbench import Dataset as BaseDataset
from bs4 import BeautifulSoup as bs
from clldutils import jsonlib
from clldutils.misc import lazyproperty
from clldutils.path import walk
from pybtex import database

from imtvaultcommands.util.lsp import Record


def fix_bibtex(s):
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
                self.file_dict[filename.name] = s
            except UnicodeDecodeError as e:
                #print(e)
                if log:
                    log.warning("Unicode problem in %s" % filename)
                continue

    def __iter__(self):
        yield from ((self.dir / fn, fn, tex, self.languages.get(fn))
                    for fn, tex in sorted(self.file_dict.items()))

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
            res = self.get_abbreviations(self.file_dict[abbrfile])
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
                        yield ex, fn
                        seen.add(ex.ID)


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "imtvault"

    def cldf_specs(self):  # A dataset must declare all CLDF sets it creates.
        return super().cldf_specs()

    def dump_extracted_examples(self, examples, fname):
        if examples:
            jsonlib.dump(
                examples,
                self.dir / 'extracted_examples' / fname,
                sort_keys=True, indent=4, ensure_ascii=False)

    def iter_extracted_examples(self):
        for p in self.dir.joinpath('extracted_examples').glob('*json'):
            with jsonlib.update(p, sort_keys=True, indent=4, ensure_ascii=False) as json:
                yield from json

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
        def get_bibtex(book_id):
            res = urllib.request.urlopen('https://langsci-press.org/catalog/book/{}'.format(book_id))
            soup = bs(res.read().decode('utf8'), features='html.parser')
            for button in soup.find_all('button'):
                if button.text == 'Copy BibTeX':
                    res = button['onclick'].replace("copyToClipboard('", '').replace("')", '').replace('<br>', '\n')
                    return re.sub(r'@([a-z]+){([^,]+),', lambda m: '@{}{{lsp{},'.format(m.groups()[0], str(book_id)), res)

        missing = set()
        abbrs = collections.Counter()
        for p in tqdm(list(self.dir.joinpath('extracted_examples').glob('*.json'))):
            for ex in load(p):
                #abbrs.update([clean_abbr(k) for k in (ex['abbrkey'] or {}).keys() if not re.fullmatch('[0-9A-Z]+', clean_abbr(k))])
                #continue
                op = self.etc_dir / 'bibtex' / '{}.bib'.format(ex['book_ID'])
                if not op.exists() and (ex['book_ID'] not in missing):
                    bibtex = get_bibtex(ex['book_ID'])
                    if bibtex:
                        op.write_text(bibtex, encoding='utf8')
                    else:
                        missing.add(ex['book_ID'])
        for k, v in abbrs.most_common():
            print(k, v)

    def cmd_makecldf(self, args):
        args.writer.cldf.add_component(
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
        args.writer.cldf.add_component(
            'ExampleTable',
            {
                'name': 'LGR_Conformance_Level',
                'datatype': {
                    'base': 'string',
                    'format': '|'.join(re.escape(str(l)) for l in LGRConformance)}
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
        )

        def filtered(l, c):
            return list(recombine([clean(k.replace('\\t', '__t'), c) for k in l if k not in ['{}', '', '--']]))

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

        def get_abbrs(d):
            res = {}
            for k, v in (d or {}).items():
                k = clean_abbr(k)
                if k:
                    res[k] = v
            return res

        with_source = set()
        for p in sorted(self.etc_dir.joinpath('bibtex').glob('*.bib'), key=lambda pp: int(pp.stem)):
            with_source.add(p.stem)
            args.writer.cldf.sources.add(fix_bibtex(p.read_text(encoding='utf8')))

        tex = collections.Counter()
        lgs = collections.Counter()
        mlgs = {}
        seen = set()
        for p in self.dir.joinpath('extracted_examples').glob('*.json'):
            fname = re.sub('store-[0-9]+-', '', p.stem) + 'tex'
            for ex in load(p):
                # FIXME:
                # - abbrkey
                #
                try:
                    if str(ex['book_ID']) not in with_source:
                        continue  # Either an unpublished or a superseded book.
                except:
                    print(p)
                    print(ex)
                    raise

                obj = filtered(ex['srcwordsbare'], tex)
                gloss = filtered(ex['imtwordsbare'], tex)
                if not (obj and gloss):
                    assert obj == gloss == []
                    continue  # No primary text or gloss.
                assert all(s for s in obj) and all(s for s in gloss)

                if ex['book_metalanguage'] and ex['book_metalanguage'] not in mlgs:
                    glang = args.glottolog.api.cached_languoids[args.glottolog.api.glottocode_by_iso[ex['book_metalanguage']]]
                    mlgs[ex['book_metalanguage']] = glang.id
                    args.writer.objects['LanguageTable'].append(dict(
                        ID=glang.id,
                        Name=glang.name,
                        Glottocode=glang.id,
                        Latitude=glang.latitude,
                        Longitude=glang.longitude,
                    ))

                if ('language_glottocode' not in ex) or not ex['language_glottocode']:
                    ex['language_glottocode'] = 'und'

                if ex['language_glottocode'] not in lgs:
                    glang = None
                    if ex['language_glottocode'] != 'und':
                        glang = args.glottolog.api.cached_languoids[ex['language_glottocode']]
                    if not glang or (glang.iso not in mlgs):
                        args.writer.objects['LanguageTable'].append(dict(
                            ID=ex['language_glottocode'],
                            Name=ex['language_name'] or (glang.name if glang else 'Undefined'),
                            Glottocode=glang.id if glang else None,
                            Latitude=glang.latitude if glang else None,
                            Longitude=glang.longitude if glang else None,
                        ))
                    if glang and glang.iso:
                        mlgs[glang.iso] = glang.id

                lgs.update([ex['language_glottocode']])
                tr = ex['trs']
                igt = IGT(
                    phrase=' '.join(obj),
                    gloss=' '.join(gloss),
                    abbrs=get_abbrs(ex['abbrkey']),
                )
                conformance = igt.conformance
                ID = '{}-{}'.format(ex['book_ID'], ex['ID']).replace('.', '_')
                if ID in seen:
                    #print('+++dup+++', p.name, ID)
                    continue
                seen.add(ID)

                args.writer.objects['ExampleTable'].append(dict(
                    ID=ID,
                    Language_ID=ex['language_glottocode'],
                    Meta_Language_ID=mlgs.get(ex['book_metalanguage']),
                    Primary_Text=igt.primary_text,
                    Analyzed_Word=obj if conformance > LGRConformance.UNALIGNED else [],
                    Gloss=gloss if conformance > LGRConformance.UNALIGNED else [],
                    Translated_Text=tr,
                    LGR_Conformance_Level=str(conformance),
                    Abbreviations=igt.gloss_abbrs if conformance == LGRConformance.MORPHEME_ALIGNED else {},
                    Source=['lsp{}'.format(ex['book_ID'])],
                    #
                    # FIXME: add comment!
                    #
                ))

        for lg in args.writer.objects['LanguageTable']:
            if lg['ID'] != 'und':
                lg['Examples_Count'] = lgs.get(lg['ID'], 0)
                lg['Examples_Count_Log'] = math.log(lgs.get(lg['ID'], 1))
        #for k, v in lgs.most_common():
        #    print(k, v)
        #for k, v in tex.most_common(100):
        #    print(k, v)
