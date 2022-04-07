import glob
import sys
import re
import sre_constants
import pprint
import json
import operator
import os
import LaTexAccents
import requests
import hashlib

from bs4 import BeautifulSoup
from collections import defaultdict
from titlemapping import titlemapping
from lgrlist import LGRLIST

from imtvaultconstants import *

converter = LaTexAccents.AccentConverter()

try:
    glottonames = json.loads(open("glottonames.json").read())
except FileNotFoundError:
    glottonames = {}

try:
    glotto_iso6393 = json.loads(open("glottoiso.json").read())
except FileNotFoundError:
    glotto_iso6393 = {}

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
    ):
        basename = filename.split("/")[-1]
        self.license = "https://creativecommons.org/licenses/by/4.0"
        self.book_ID = int(filename.split("/")[-2])
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
            if lg not in ("", None):
                self.language_name = lg
                try:
                    self.language_glottocode = glottonames[lg][0]
                    glottonames[lg] = [self.language_glottocode, None]
                    self.language_iso6393 = get_iso(self.language_glottocode)
                except KeyError:
                    if glottotmp.get(lg):
                        self.language_glottocode = None
                    else:
                        request_url = f"https://glottolog.org/glottolog?name={lg}&namequerytype=part"
                        print(lg, request_url)
                        html = requests.get(request_url).text
                        soup = BeautifulSoup(html, "html.parser")
                        languoids = soup.find_all("a", class_="Language")
                        if len(languoids) == 3:  # exactly one languoid
                            self.language_glottocode = languoids[0][
                                "title"
                            ]
                            self.language_family = languoids[2]["title"]
                            self.language_name = lg
                            print(" " + self.language_glottocode)
                            glottonames[lg] = [self.language_glottocode, None]
                        elif (
                            len(languoids) == 0
                        ):  # no languoids. We store this in persistent storage
                            print(len(languoids))
                            glottonames[lg] = [None, None]
                        else:  # more than one languoid.  We check whether Glottolog has exactly one "language"
                            print(len(languoids))
                            languoids2 = soup.find_all("td", class_="level-language")
                            print(len(languoids2))
                            if len(languoids2) == 1:
                                self.language_glottocode = (
                                    languoids2[0]
                                    .find("a", class_="Language")["href"]
                                    .split("/")[-1]
                                )
                                self.language_name = lg
                                glottonames[lg] = [self.language_glottocode, None]
                                print(" " + self.language_glottocode)
                                # self.language_family = FIXME
                            else: #Glottolog has no clear indication of the language. We keep this information in temporary storage
                                self.language_glottocode = None
                                glottotmp[lg] = True
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
        d = {}
        smallcaps = re.findall("\\\\textsc\{([-=.:a-zA-Z0-9)(/\[\]]*?)\}", s)
        for sc in smallcaps:
            cats = re.split("[-=.:0-9)(/\[\]]", sc)
            for cat in cats:
                d[cat] = True
        return sorted(list(d.keys()))

    #def json(self):
        #print(json.dumps(self.__dict__, sort_keys=True, indent=4))

    #def __str__(self):
        #return "%s\n%s\n%s\n" % (self.srcwordshtml, self.imtwordshtml, self.trs)

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


def get_iso(glottocode):
    global glotto_iso6393
    if glottocode == None:
        return "und"
    try:
        return glotto_iso6393[glottocode]
    except KeyError:
        request_url = f"https://glottolog.org/resource/languoid/id/{glottocode}"
        html = requests.get(request_url).text
        soup = BeautifulSoup(html, "html.parser")
        try:
            iso = soup.find("span", class_="iso639-3").a["title"]
        except AttributeError:
            return "und"
        glotto_iso6393[glottocode] = iso
        print(glottocode, iso)
        return iso



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


def langsciextract(directory):
    globstring = f"{directory}/*"
    books = glob.glob(globstring)
    # books = glob.glob(f"{directory}/16")
    for book in books:
        book_ID = int(book.split("/")[-1])
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
        glossesd = defaultdict(int)
        excludechars = ".\\}{=~:/"
        abbrkey = {}
        try:
            with open(f"{directory}/{book_ID}/abbreviations.tex") as abbrin:
                abbrkey = get_abbreviations(abbrin.readlines())
        except FileNotFoundError:
            pass
        files = glob.glob(f"{directory}/{book_ID}/chapters/*tex")
        files = glob.glob(f"{directory}/{book_ID}/*tex")
        # print(" found %i tex files for %s" % (len(files), book_ID))
        for filename in files:
            try:
                s = open(filename).read()
            except UnicodeDecodeError:
                print("Unicode problem in %s" % filename)
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
                lg = g["language_name"]
                if g["imtline2"] in (None, ""):  # standard \gll example¨
                    src = g["sourceline"]
                    imt = g["imtline1"]
                else:
                    # we ignore the first line of \glll examples as the second line typically contains the morpheme breaks
                    src = g["imtline1"]
                    imt = g["imtline2"]
                trs = g["translationline"]
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
                    )
                    if thisgll.book_ID in NON_CCBY_LIST:
                        continue
                except AssertionError:
                    continue
                examples.append(thisgll)
            if examples != []:
                jsons = json.dumps(
                    [ex.__dict__ for ex in examples],
                    sort_keys=True,
                    indent=4,
                    ensure_ascii=False,
                )
                try:
                    os.mkdir('langscijson')
                except FileExistsError:
                    pass
                jsonname = "langscijson/%sexamples.json" % filename[:-4]\
                            .replace("/", "-")\
                            .replace("raw-raw_texfiles-raw-", "")
                print("   ", jsonname)
                with open(jsonname, "w", encoding="utf8") as jsonout:
                    jsonout.write(jsons)
    with open("glottonames.json", "w") as namesout:
        namesout.write(
            json.dumps(glottonames, sort_keys=True, indent=4, ensure_ascii=False)
        )
    with open("glottoiso.json", "w") as glottoisoout:
        glottoisoout.write(
            json.dumps(glotto_iso6393, sort_keys=True, indent=4, ensure_ascii=False)
        )

if __name__ == "__main__":
    langsciextract('raw/raw_texfiles/raw')
