import hashlib
import collections

import attr
from . import LaTexAccents
from .titlemapping import titlemapping

from .imtvaultconstants import *

converter = LaTexAccents.AccentConverter()
glottotmp = {}


def strip_tex_comment(s):
    return re.split(r"(?<!\\)%", s)[0].replace(r"\%", "%")


def resolve_lgr(s):
    s = re.sub(LGRPATTERN_UPPER, r"\1", s)
    for m in LGRPATTERN_LOWER.findall(s):
        g = m[0]
        s = re.sub(r"\\%s(?![a-zA-Z])" % g, g.upper(), s)
    for m in LGRPATTERN_UPPER_LOWER.findall(s):
        g = m[0]
        s = re.sub(r"\\%s(?![a-zA-Z])" % g, g.upper(), s)
    return s


def tex2html(s):
    result = striptex(s, html=True)
    # repeated for nested  \textsomething{\textsomethingelse{}}
    result = TEXTEXT.sub('<span class="\\1">\\2</span>', result)
    result = TEXTEXT.sub('<span class="\\1">\\2</span>', result)
    result = TEXTEXT.sub('<span class="\\1">\\2</span>', result)
    return result


def striptex(s, sc2upper=False, html=False):
    result = converter.decode_Tex_Accents(s, utf8_or_ascii=1)
    if sc2upper:
        for m in re.findall("\\\\textsc{([-\.:=<> a-zA-Z0-9]*?)}", result):
            result = result.replace("\\textsc{%s}" % m, m.upper())
    result = re.sub(INDEXCOMMANDS, "", result)
    result = re.sub(LABELCOMMANDS, "", result)
    result = re.sub(TEXSTYLEENVIRONMENT, r"\1", result)
    for r in TEXREPLACEMENTS:
        result = result.replace(*r)
    for r in TEXTARGYANKS:
        result = re.sub(r"\\%s{.*?}" % r, "", result)
    result = re.sub(r"\footnote{[^}{]*}", "", result)
    # add " " in front of string so that lookbehind matches if at beginning of line
    result = re.sub(BRACESPATTERN, r"\1", " " + result)[1:]
    # strip "\ " (latex protected space)
    result = re.sub(r"(?<!\\)\\ ", " ", result)
    if html:  # keep \textbf, \texit for the time being, to be included in <span>s
        return result
    # repeat  for nested  \textsomething{\textsomethingelse{}}
    result = re.sub(TEXTEXT, "\\2", result)
    result = re.sub(TEXTEXT, "\\2", result)
    result = re.sub(BRACESPATTERN, r"\1", " " + result)[1:]
    return re.sub(TEXTEXT, "\\2", result)


def tex2categories(s):
    d = set()
    smallcaps = re.findall("\\\\textsc\{([-=.:a-zA-Z0-9)(/\[\]]*?)\}", s)
    for sc in smallcaps:
        cats = re.split("[-=.:0-9)(/\[\]]", sc)
        for cat in cats:
            if cat:
                d.add(cat)
    return sorted(d)


def clean_translation(trs):
    trs = trs.replace("\\\\", " ").strip()
    try:
        if trs[0] in STARTINGQUOTE:
            trs = trs[1:]
        if trs[-1] in ENDINGQUOTE:
            trs = trs[:-1]
        trs = strip_tex_comment(trs)
        trs = striptex(trs)
        trs = trs.replace("()", "")
    except IndexError:  # s is  ''
        pass
    m = CITATION.search(trs)
    if m is not None:
        if m.group(2) != "":
            trs = re.sub(CITATION, r"(\2: \1)", trs).replace("[", "").replace("]", "")
        else:
            trs = re.sub(CITATION, r"(\2)", trs)
    return trs


@attr.s
class GLL:
    abbrkey = attr.ib()
    categories = attr.ib()
    book_ID = attr.ib(validator=attr.validators.instance_of(int))
    book_metalanguage = attr.ib()
    ID = attr.ib()
    html = attr.ib()
    srcwordsbare = attr.ib(validator=attr.validators.instance_of(list))
    language_iso6393 = attr.ib()
    language_glottocode = attr.ib()
    language_name = attr.ib()
    imtwordsbare = attr.ib()
    clength = attr.ib(validator=attr.validators.instance_of(int))
    citation = attr.ib()
    trs = attr.ib(converter=clean_translation)

    def json(self):
        res = attr.asdict(self)
        res.update(
            license="https://creativecommons.org/licenses/by/4.0",
            book_URL="https://langsci-press.org/catalog/book/{}".format(self.book_ID),
            book_title=titlemapping.get(self.book_ID),
            wlength=len(self.srcwordsbare),
            label=" ".join(self.srcwordsbare),
        )
        for type_ in [' and ', ' or ']:
            if type_ in self.trs:
                res['coordination'] = type_.strip()

        res["language"] = None
        if self.language_glottocode:
            if self.language_glottocode != "und":
                res["language"] = \
                    "https://glottolog.org/resource/languoid/id/{}".format(self.language_glottocode)
        else:
            del res['language_glottocode']

        for aspect, types_ in [
            ('time', [(' yesterday ', 'past'), (' tomorrow ', 'future'), (' now ', 'present')]),
            ('modality', [(' want ', 'volitive')]),
            ('polarity', [(' not ', 'negative')]),
        ]:
            for marker, type_ in types_:
                if marker in self.trs.lower():
                    res[aspect] = type_
        return res

    @classmethod
    def from_match(cls, match, p, book_ID, abbrkey, gl_by_name):
        g = match.groupdict()

        metalang = 'eng'
        for iso, book_ids in METALANGS.items():
            if book_ID in book_ids:
                metalang = iso

        # Try to identify the language:
        language = list(ONE_LANGUAGE_BOOKS.get(book_ID, (None, None, None)))
        if language[1] is None:
            lg = (g["language_name"] or '').split('{', maxsplit=1)[-1].strip()
            if lg:
                language[2] = lg
                gl = gl_by_name.get(lg)
                if gl:
                    language[1] = gl.id
                    language[0] = gl.iso

        # we ignore the first line of \glll examples if there's a second line,
        # as the second line typically contains the morpheme breaks
        src, imt = (g["imtline1"], g["imtline2"]) if g["imtline2"] \
            else (g["sourceline"], g["imtline1"])  # standard \gll example¨

        srcwordstex = strip_tex_comment(src).split()
        imtwordstex = [resolve_lgr(i) for i in strip_tex_comment(imt).split()]
        assert len(srcwordstex) == len(imtwordstex)
        imt_html = "\n".join(
            [
                '\t<div class="imtblock">\n\t\t<div class="srcblock">'
                + tex2html(t[0])
                + '</div>\n\t\t<div class="glossblock">'
                + tex2html(t[1])
                + "</div>\n\t</div>"
                for t in zip(srcwordstex, imtwordstex)
            ]
        )
        srcwordsbare = [striptex(w) for w in srcwordstex]

        citation = None
        match = CITATION.search(g["presourceline"] or "") or CITATION.search(g["translationline"])
        if match:
            citation = match.group(2)

        return cls(
            abbrkey=abbrkey,
            categories=tex2categories(imt or ""),
            book_ID=book_ID,
            book_metalanguage=metalang,
            ID="{}-{}".format(
                p.stem,
                hashlib.sha256(" ".join(srcwordsbare).encode("utf-8")).hexdigest()[:10]),
            html='<div class="imtblocks">\n{}\n</div>\n'.format(imt_html),
            srcwordsbare=srcwordsbare,
            language_iso6393 = language[0],
            language_glottocode = language[1],
            language_name = language[2],
            imtwordsbare=[striptex(w, sc2upper=True) for w in imtwordstex],
            clength=len(src),
            citation=citation,
            trs=g["translationline"],
        )


def get_abbreviations(tex):
    result = {}
    for line in tex.split('\n'):
        if line.strip().startswith("%"):
            continue
        cells = line.split("&")
        if len(cells) == 2:
            abbreviation = resolve_lgr(striptex(cells[0]).strip())
            if abbreviation == "...":
                continue
            expansion = striptex(cells[1]).replace(r"\\", "").strip().replace(r"\citep", "")
            result[abbreviation] = expansion
    return result


def get_abbrkey(tex):
    abbrfile = 'abbreviations.tex'
    abbrkey = {}
    if abbrfile in tex:
        abbrkey = get_abbreviations(tex[abbrfile][1])
    if not abbrkey:
        for p, s in tex.values():
            if p.name != abbrfile:
                try:
                    abbr = s.split("section*{Abbreviations}")[1]
                    abbrkey = get_abbreviations(abbr.split(r"\section")[0])
                    if abbrkey:
                        break
                except IndexError:
                    pass
    return abbrkey


def iter_tex(book):
    for filename in book.glob('*tex'):
        try:
            s = filename.read_text(encoding='utf8')
        except UnicodeDecodeError:
            print("Unicode problem in %s" % filename)
            continue
        s = s.replace(r"{\bfseries ", r"\textbf{")
        s = s.replace(r"{\itshape ", r"\textit{")
        s = s.replace(r"{\scshape ", r"\textsc{")
        yield filename.name, (filename, s)


def langsciextract(ds, gl_by_name):
    unknown_lgs = collections.Counter()
    for book_ID, book in ds.iter_tex_dirs():
        if (book_ID in SUPERSEDED) or (book_ID in NON_CCBY_LIST):
            continue
        tex = dict(iter_tex(book))
        abbrkey = get_abbrkey(tex)

        for filename, s in tex.values():
            examples = []
            for match in GLL_PATTERN.finditer(s):
                try:
                    gll = GLL.from_match(match, filename, book_ID, abbrkey, gl_by_name)
                except AssertionError:
                    continue
                if gll.language_name and not gll.language_glottocode:
                    unknown_lgs.update([gll.language_name])
                examples.append(gll.json())
            ds.dump_extracted_examples(
                examples, 'store-{}-{}examples.json'.format(book_ID, filename.stem))
    #for k, v in unknown_lgs.most_common(50):
    #    print(k, v)
