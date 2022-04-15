import hashlib
import collections

import attr
from pyigt.igt import NON_OVERT_ELEMENT

from . import LaTexAccents
from .titlemapping import titlemapping

from .imtvaultconstants import *

EMPTY = NON_OVERT_ELEMENT
ELLIPSIS = '…'
converter = LaTexAccents.AccentConverter()
glottotmp = {}


def strip_tex_comment(s):
    lines = re.split(r'\\\\', s)
    if len(lines) == 2 and lines[1].startswith('%'):
        s = lines[0] + r'\\'
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
            s = s.replace(r'\langinfobreak', r'\langinfo')
            s = s.replace(r'{\db}{\db}{\db}', '[[[')
            s = s.replace(r'{\db}{\db}', '[[')
        except UnicodeDecodeError:
            print("Unicode problem in %s" % filename)
            continue
        yield filename.name, (filename, s)


def parse_langinfo(l):
    from TexSoup import TexSoup
    from TexSoup.data import TexCmd

    # FIXME: extract page numbers, too!

    def get_name(arg):
        if len(arg.contents) == 1 and isinstance(arg.contents[0], TexCmd) and not arg.contents[0].args:
            return '\\' + arg.contents[0].name
        return ''.join(TexSoup(re.sub(r'\\label{[^}]+}', '', arg.string)).text)

    langinfo = TexSoup(r'\langinfo' + l.split(r'\langinfo')[-1], tolerance=1).langinfo
    if langinfo and len(langinfo.args) == 3:
        return (
            get_name(langinfo.args[0]),
            ''.join(TexSoup(langinfo.args[1].string).text),
            (TexSoup(langinfo.args[2].string).text or [''])[-1],
        )


def parse_ili(l):
    from TexSoup import TexSoup
    try:
        ili = TexSoup(r'\ili{' + l.split(r'\ili{')[-1].split('}')[0], tolerance=1).ili
    except:
        raise ValueError(l)
    return (ili.args[0].string, '', '')


def parse_il(l):
    from TexSoup import TexSoup
    try:
        il = TexSoup(r'\il{' + l.split(r'\il{')[-1].split('}')[0], tolerance=1).il
    except:
        raise ValueError(l)
    return (il.args[0].string.split('!')[-1], '', '')


def iter_gll(s):
    gll_start = re.compile(r'\\gll(l)?[^a-zA-Z]')
    glt_start = re.compile(r'\\(glt|trans)[^a-zA-Z]')
    longexampleandlanguage_pattern = re.compile(r'\\\\}{([^}]+)}$')

    linfo = None
    ex_pattern = re.compile(r"\\ex\s+(?P<lname>[A-Z][a-z]+)\s+(\([A-Z][0-9],\s+)?\\cite[^{]+{(?P<ref>[^}]+)}")
    gll, in_gll = [], False
    for lineno, line in enumerate(s.split('\n')):
        line = strip_tex_comment(line).strip()
        if r'\langinfo' in line:
            res = parse_langinfo(line)
            if res:
                linfo = (res, lineno)
        elif r'\ili{' in line:
            res = parse_ili(line)
            if res:
                linfo = (res, lineno)
                #line, rem = line.split(r'\ili{', maxsplit=1)
                #line += rem.split('}', maxsplit=1)[1] if '}' in rem else ''
                line = line.replace('()', '').strip()
        elif r'\il{' in line:
            res = parse_il(line)
            if res:
                linfo = (res, lineno)
                line, rem = line.split(r'\il{', maxsplit=1)
                line += rem.split('}', maxsplit=1)[1] if '}' in rem else ''
                line = line.replace('()', '').strip()
        elif ex_pattern.match(line):
            m = ex_pattern.match(line)
            linfo = ((m.group('lname'), '', m.group('ref')), lineno)

        m = glt_start.search(line)
        if m:
            if gll and len(gll) < 10:
                #
                # We may need to fix the gloss line:
                mm = longexampleandlanguage_pattern.search(gll[-1])
                if mm:
                    linfo = ((mm.groups()[0], '', ''), lineno)
                    gll[-1] = gll[-1][:mm.start()]
                pre = line[:m.start()]
                line = line[m.end() - 1:]
                gll.append(pre)
                gll.append(line)
                # Return linfo it wasn't parsed too far from the example:
                yield linfo[0] if linfo and (lineno - linfo[1] < 25) else None, gll
            gll, in_gll = [], False
            continue
        m = gll_start.search(line)
        if m:
            line = line[m.end() - 1:]
            gll = []
            in_gll = True
        if in_gll:
            gll.append(line)


# per chapter "one language":
ONE_LANGUAGE_CHAPTERS = {
    '173/04-me.tex': 'Spanish',
    '306/owusu.tex': 'Akan',
    '271/04.tex': 'Hebrew',
    '137/ch3.tex': 'Tashlhiyt',
    '254/08-dalessandro.tex': 'Ripano',
    '254/04-smith.tex': 'Ostyak',
    '120/mwamzandi.tex': 'Swahili',
    '189/06.tex': 'Russian',
}


def recombine(l):
    from pyigt.lgrmorphemes import MORPHEME_SEPARATORS
    chunk = []
    for c in l:
        if not c:
            continue
        if c[0] in MORPHEME_SEPARATORS or (chunk and chunk[-1][-1] in MORPHEME_SEPARATORS):
            chunk.append(c)
        else:
            if chunk:
                yield ''.join(chunk)
            chunk = [c]
    if chunk:
        yield ''.join(chunk)


CHAR_REPLS = {
    r'\v{s}': 'š',
    r"\'u": 'ú',
    r'\v{h}': "ȟ",
    r"\'a": "á",
}


def fixed_alignment(pt, gl):
    from .latex import to_text

    # pre-process
    # Merge multi-word lexical glosses:
    multi_word_gloss = re.compile(r'(\s|^){([Ia-z ]+|North Wales|The birds)}(\s|,|$)')
    gl = multi_word_gloss.sub(
        lambda m: ' {} '.format(re.sub(r'\s+', '_', m.groups()[1])), gl).strip()
    gl = re.sub(r'(\s|^){}(\s|$)', ' _ ', gl.replace('{} {}', '{}  {}'))
    gl = re.sub(r'(\s|^){}{}(\s|$)', ' _ ', gl)
    gl = re.sub(r'(\s|^)~(\s|$)', ' _ ', gl)

    # Merge multi-word primary text groups:
    for k, v in CHAR_REPLS.items():
        pt = pt.replace(k, v)
    multi_word_pt = re.compile(r'(\s|^){([\w žąį./]+)}(\s|\.|$)')
    pt = multi_word_pt.sub(
        lambda m: ' {} '.format(re.sub(r'\s+', '_', m.groups()[1])), pt).strip()
    pt = re.sub(r'(\s|^){}(\s|$)', ' _ ', pt)

    comment = None

    # de-latex
    pt = to_text(pt)[0].split()
    gl = to_text(gl)[0].split()

    # post-process
    ellipsis_variants = [
        '....', '[…]', '[...]', '...', '[...].', '“…”', '[…].', '(...).', '…]']
    pt = [ELLIPSIS if w in ellipsis_variants else w for w in pt]
    gl = [ELLIPSIS if w in ellipsis_variants else w for w in gl]

    if len(pt) > len(gl):
        if pt[-1] == '.':
            pt = pt[:-1]
            pt[-1] += '.'
        elif pt[-1] == '[]':
            pt = pt[:-1]

    ldiff = len(pt) - len(gl)
    if ldiff == -1:
        if gl and gl[-1].startswith('[') and gl[-1].endswith(']'):
            comment = gl[-1][1:-1].strip()
            gl = gl[:-1]
    elif ldiff == 1:
        if ELLIPSIS in pt:
            gl.insert(pt.index(ELLIPSIS), ELLIPSIS)
        elif '/' in pt:
            gl.insert(pt.index('/'), '/')
        elif EMPTY in pt:
            gl.insert(pt.index(EMPTY), EMPTY)
        elif EMPTY + '.' in pt:
            gl.insert(pt.index(EMPTY + '.'), EMPTY)
        elif pt[-1] in [']', '].', ']?']:
            gl.append('_')
        elif re.fullmatch(r'\([^)]+\)', pt[-1]):
            comment = pt[-1].replace('(', '').replace(')', '')
            pt = pt[:-1]

    ldiff = len(pt) - len(gl)
    if ldiff > 0:
        if ldiff == pt.count(ELLIPSIS):
            for i, c in enumerate(pt):
                if c == ELLIPSIS:
                    gl.insert(i, ELLIPSIS)
        elif ldiff == pt.count('<') + pt.count('>'):
            for i, c in enumerate(pt):
                if c in ['<', '>']:
                    gl.insert(i, '_')

    pt_r, gl_r = list(recombine(pt)), list(recombine(gl))
    if len(pt_r) == len(gl_r):
        pt, gl = pt_r, gl_r
    return pt, gl, comment


def lines_and_comment(lines):
    """
    Figure out which lines of all lines between \gll and \glt to be considered as
    word/morpheme-segmented primary text and gloss.

    :param lines:
    :return:
    """
    from .latex import to_text
    from TexSoup import TexSoup
    res, comment, linfo = [], [], None
    for line in lines:
        line = line.strip()
        if line:
            try:
                s = TexSoup(line, tolerance=1)
                if s.jambox:
                    comment.append(s.jambox.string)
                    s.jambox.delete()
                    line = str(s)
            except:
                pass
            if line:
                res.append(line)
    if len(res) > 2:
        # Language names as second argument to "longexampleandlanguage" commands.
        m = re.fullmatch(r'}{([A-Z][a-z]+)}', res[-1].split('\n')[0])
        if m:
            linfo = (m.groups()[0], '', '')
            res = res[:-1]
        else:
            # Comments in square brackets appended to the example.
            m = re.fullmatch(r'\[([\w ]+)]', to_text(res[-1].split('\n')[0])[0].strip())
            if m:
                comment = m.groups()[0]
                res = res[:-1]
            else:
                # A single word: Considered a comment.
                m = re.fullmatch(r'([\w]+)', to_text(res[-1].split('\n')[0])[0].strip())
                if m:
                    comment = m.groups()[0]
                    res = res[:-1]
                else:
                    # Language names appended as special comment in parentheses to the example.
                    m = re.fullmatch(r'\(?([A-Z][a-z]+(-English)?|[0-9/]+|[A-Z][A-Z]+)\)?', to_text(res[-1].split('\n')[0])[0].strip())
                    if m:
                        if m.groups()[0][0].isalpha() and m.groups()[0][0].islower():
                            linfo = (m.groups()[0], '', '')
                        else:
                            comment = m.groups()[0]
                        res = res[:-1]
    return [r.replace('\n', ' ') for r in res], '; '.join(comment), linfo


def langsciextract(ds, gl_by_name, bid):
    from .latex import to_text
    unknown_lgs = collections.Counter()
    macros = collections.Counter()
    macroex = {}
    mp = re.compile(r'\\([a-zA-Z]+)[^a-zA-Z]')
    ii, xx = 0, 0
    allex = collections.Counter()
    invex = collections.Counter()
    for book_ID, book in ds.iter_tex_dirs():
        if (book_ID in SUPERSEDED) or (book_ID in NON_CCBY_LIST):
            continue
        if bid and (book_ID != int(bid)):
            continue
        tex = dict(iter_tex(book))
        abbrkey = get_abbrkey(tex)

        for filename, s in tex.values():
            for linfo, gll in iter_gll(s):
                if linfo:
                    linfo = [to_text(s or '')[0] for s in linfo]
                #for line in gll:
                #    for m in mp.finditer(line):
                #        macros.update([m.groups()[0]])
                #        macroex[m.groups()[0]] = line
                #continue

                aligned, translation = '\n'.join(gll[:-1]), gll[-1]
                aligned = [l.strip() for l in re.split(r'\\(?:\\|newline)', aligned) if l.strip()]
                # book-specifics:
                if book_ID == 212:
                    if len(aligned) > 2:
                        if 'footnotesize' in aligned[2]:
                            aligned = aligned[:2]

                #
                # must remove stuff like \jambox{...}
                #
                aligned, comment, linfo2 = lines_and_comment(aligned)
                aligned = [l for l in aligned if to_text(l)[0].replace('*', '').strip()]
                if len(aligned) == 3:
                    # There's a separate line for the morpheme-segmented primary text!
                    obj, pt, gl = aligned
                elif len(aligned) == 2:
                    pt, gl = aligned
                    obj = pt
                else:
                    print(filename)
                    print(len(aligned), aligned)
                    print('---')
                    continue

                ii += 1
                allex.update([book_ID])
                pt, gl, comment = fixed_alignment(pt, gl)
                if len(pt) == len(gl):
                    continue
                if gl and gl[-1] in ['()', '*()']:
                    gl = gl[:-1]
                if len(pt) == len(gl):
                    continue
                xx += 1
                invex.update([book_ID])
                print(filename.parent.name, filename.name, linfo)
                print(re.sub(r'\s+', ' ', to_text(obj)[0]))
                #print(len(pt), pt)
                #print(len(gl), gl)
                print('\t'.join(pt))
                print('\t'.join(gl))
                print(to_text(translation)[0])

                print('------')
                continue
                if not linfo:
                    if 'longexampleandlanguage' in gll:
                        pass
                        # TexSoup(gll, tolerance=1).longexampleandlanguage.args[1].string
                    elif book_ID in ONE_LANGUAGE_BOOKS:
                        pass
                    elif '{}/{}'.format(book_ID, filename.name) in ONE_LANGUAGE_CHAPTERS:
                        pass
                    else:
                        ii += 1
                        #print(filename)
                        #print(gll)
                        #print('+++', linfo)
                        #print('-----------------------------------------')
                break
            continue
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
    print(ii, xx)
    #for k, v in macros.most_common():
    #    print('{}\t{}\t{}\t{}'.format(k, v, macroex[k], to_text(macroex[k])))
    for k, v in invex.most_common(30):
        print(k, v, allex[k], '{}%'.format(round(100 * float(v)/allex[k])))
