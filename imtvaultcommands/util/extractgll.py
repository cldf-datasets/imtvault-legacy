import hashlib
import collections

from clldutils import jsonlib
from . import LaTexAccents
from .titlemapping import titlemapping

from .imtvaultconstants import *

converter = LaTexAccents.AccentConverter()
glottotmp = {}

class gll:
    def __init__(
        self,
        presource,
        lg,
        src,
        imt,
        trs,
        filename=None,
        booklanguage=None,
        book_metalanguage="eng",
        abbrkey=None,
        gl_by_name=None,
    ):
        basename = filename.name
        self.license = "https://creativecommons.org/licenses/by/4.0"
        self.book_ID = int(filename.parent.name)
        self.book_URL = f"https://langsci-press.org/catalog/book/{self.book_ID}"
        self.book_title = titlemapping.get(self.book_ID)
        self.book_metalanguage = book_metalanguage
        self.abbrkey = abbrkey
        self.categories = self.tex2categories(imt)
        srcwordstex = self.strip_tex_comment(src).split()
        imtwordstex = [self.resolve_lgr(i) for i in self.strip_tex_comment(imt).split()]
        assert len(srcwordstex) == len(imtwordstex)
        imt_html = "\n".join(
            [
                '\t<div class="imtblock">\n\t\t<div class="srcblock">'
                + self.tex2html(t[0])
                + '</div>\n\t\t<div class="glossblock">'
                + self.tex2html(t[1])
                + "</div>\n\t</div>"
                for t in zip(srcwordstex, imtwordstex)
            ]
        )
        self.html = f'<div class="imtblocks">\n{imt_html}\n</div>\n'
        self.srcwordsbare = [self.striptex(w) for w in srcwordstex]
        self.ID = "%s-%s" % (
            basename.replace(".tex", "").split("/")[-1],
            hashlib.sha256(" ".join(self.srcwordsbare).encode("utf-8")).hexdigest()[
                :10
            ],
        )
        self.imtwordsbare = [self.striptex(w, sc2upper=True) for w in imtwordstex]
        self.clength = len(src)
        self.wlength = len(self.srcwordsbare)

        self.citation = None
        match = CITATION.search(presource) or CITATION.search(trs)
        if match:
            self.citation = match.group(2)

        self.trs = trs.replace("\\\\", " ").strip()
        try:
            if self.trs[0] in STARTINGQUOTE:
                self.trs = self.trs[1:]
            if self.trs[-1] in ENDINGQUOTE:
                self.trs = self.trs[:-1]
            self.trs = self.strip_tex_comment(self.trs)
            self.trs = self.striptex(self.trs)
            self.trs = self.trs.replace("()", "")
        except IndexError:  # s is  ''
            pass
        m = CITATION.search(self.trs)
        if m is not None:
            if m.group(2) != "":
                self.trs = (
                    re.sub(CITATION, r"(\2: \1)", self.trs)
                    .replace("[", "")
                    .replace("]", "")
                )
            else:
                self.trs = re.sub(CITATION, r"(\2)", self.trs)

        if booklanguage:
            self.language_iso6393 = booklanguage[0]
            self.language_glottocode = booklanguage[1]
            self.language_name = booklanguage[2]
        else:
            self.language_iso6393 = None
            self.language_name = None
            if (lg not in ("", None)) and lg:
                self.language_name = lg
                gl = gl_by_name.get(lg)
                if gl:
                    self.language_glottocode = gl.id
                    self.language_iso6393 = gl.iso
        self.analyze()

    def strip_tex_comment(self, s):
        return re.split(r"(?<!\\)%", s)[0].replace(r"\%", "%")

    def resolve_lgr(self, s):
        s = re.sub(LGRPATTERN_UPPER, r"\1", s)
        for m in LGRPATTERN_LOWER.findall(s):
            g = m[0]
            s = re.sub(r"\\%s(?![a-zA-Z])" % g, g.upper(), s)
        for m in LGRPATTERN_UPPER_LOWER.findall(s):
            g = m[0]
            s = re.sub(r"\\%s(?![a-zA-Z])" % g, g.upper(), s)
        return s

    def tex2html(self, s):
        result = self.striptex(s, html=True)
        # repeated for nested  \textsomething{\textsomethingelse{}}
        result = TEXTEXT.sub('<span class="\\1">\\2</span>', result)
        result = TEXTEXT.sub('<span class="\\1">\\2</span>', result)
        result = TEXTEXT.sub('<span class="\\1">\\2</span>', result)
        return result

    def striptex(self, s, sc2upper=False, html=False):
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
        else:
            #repeat  for nested  \textsomething{\textsomethingelse{}}
            result = re.sub(TEXTEXT, "\\2", result)
            result = re.sub(TEXTEXT, "\\2", result)
            result = re.sub(BRACESPATTERN, r"\1", " " + result)[1:]
            return re.sub(TEXTEXT, "\\2", result)

    def tex2categories(self, s):
        d = set()
        smallcaps = re.findall("\\\\textsc\{([-=.:a-zA-Z0-9)(/\[\]]*?)\}", s)
        for sc in smallcaps:
            cats = re.split("[-=.:0-9)(/\[\]]", sc)
            for cat in cats:
                if cat:
                    d.add(cat)
        return sorted(d)

    def analyze(self):
        if " and " in self.trs:
            self.coordination = "and"
        if " or " in self.trs:
            self.coordination = "or"
        if " yesterday " in self.trs.lower():
            self.time = "past"
        if " tomorrow " in self.trs.lower():
            self.time = "future"
        if " now " in self.trs.lower():
            self.time = "present"
        if " want" in self.trs.lower():
            self.modality = "volitive"
        if " not " in self.trs.lower():
            self.polarity = "negative"


def get_abbreviations(lines):
    result = {}
    for line in lines:
        if line.strip().startswith("%"):
            continue
        cells = line.split("&")
        if len(cells) == 2:
            abbreviation = gll.resolve_lgr(None, gll.striptex(None, cells[0]).strip())
            if abbreviation == "...":
                continue
            expansion = (
                gll.striptex(None, cells[1])
                .replace(r"\\", "")
                .strip()
                .replace(r"\citep", "")
            )
            result[abbreviation] = expansion
    return result


def langsciextract(directory, outdir, gl_by_name):
    unknown_lgs = collections.Counter()
    for book in directory.iterdir():
        book_ID = int(book.name)
        if book_ID in SUPERSEDED:
            continue
        book_metalanguage = "eng"
        if book_ID in PORTUGUESE:
            book_metalanguage = "por"
        if book_ID in GERMAN:
            book_metalanguage = "deu"
        if book_ID in FRENCH:
            book_metalanguage = "fra"
        if book_ID in SPANISH:
            book_metalanguage = "spa"
        if book_ID in CHINESE:
            book_metalanguage = "cmn"
        booklanguage = ONE_LANGUAGE_BOOKS.get(int(book_ID), False)
        abbrkey = {}
        if book.joinpath("abbreviations.tex").exists():
            with book.joinpath("abbreviations.tex").open() as abbrin:
                abbrkey = get_abbreviations(abbrin.readlines())
        for filename in book.glob('*tex'):
            try:
                s = filename.read_text(encoding='utf8')
            except UnicodeDecodeError:
                print("Unicode problem in %s" % filename)
                continue
            s = s.replace(r"{\bfseries ", r"\textbf{")
            s = s.replace(r"{\itshape ", r"\textit{")
            s = s.replace(r"{\scshape ", r"\textsc{")
            if abbrkey == {}:
                try:
                    abbr1 = s.split("section*{Abbreviations}")[1]
                    abbr2 = abbr1.split(r"\section")[0]
                    abbrkey = get_abbreviations(abbr2.split("\n"))
                except IndexError:
                    pass
            examples = []
            for g in [m.groupdict() for m in GLL.finditer(s)]:
                presource = g["presourceline"] or ""
                lg = (g["language_name"] or '').split('{', maxsplit=1)[-1].strip()
                if g["imtline2"] in (None, ""):  # standard \gll example¨
                    src = g["sourceline"]
                    imt = g["imtline1"]
                else:
                    # we ignore the first line of \glll examples as the second line typically contains the morpheme breaks
                    src = g["imtline1"]
                    imt = g["imtline2"]
                trs = g["translationline"]
                if lg not in gl_by_name:
                    unknown_lgs.update([lg])
                try:
                    thisgll = gll(
                        presource,
                        lg,
                        src,
                        imt,
                        trs,
                        filename=filename,
                        booklanguage=booklanguage,
                        book_metalanguage=book_metalanguage,
                        abbrkey=abbrkey,
                        gl_by_name=gl_by_name,
                    )
                    if thisgll.book_ID in NON_CCBY_LIST:
                        continue
                except AssertionError:
                    continue
                examples.append(thisgll)
            if examples != []:
                #print("   ", outdir / 'store-{}-{}examples.json'.format(book_ID, filename.stem))
                #
                # FIXME: dump!
                #
                jsonlib.dump(
                    [ex.__dict__ for ex in examples],
                    outdir / 'store-{}-{}examples.json'.format(book_ID, filename.stem),
                    sort_keys=True, indent=4, ensure_ascii=False)
    for k, v in unknown_lgs.most_common(50):
        print(k, v)
