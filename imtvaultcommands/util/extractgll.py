import re
import hashlib
import collections

import attr
from pyigt.igt import NON_OVERT_ELEMENT

from .latex import to_text

STARTINGQUOTE = "`‘"
ENDINGQUOTE = "'’"
EMPTY = NON_OVERT_ELEMENT
ELLIPSIS = '…'


def strip_tex_comment(s):
    lines = re.split(r'\\\\', s)
    if len(lines) == 2 and lines[1].startswith('%'):
        s = lines[0] + r'\\'
    return re.split(r"(?<!\\)%", s)[0].replace(r"\%", "%")


def clean_translation(trs):
    trs = trs.replace("\\\\", " ").strip()
    try:
        if trs[0] in STARTINGQUOTE:
            trs = trs[1:]
        if trs[-1] in ENDINGQUOTE:
            trs = trs[:-1]
        if len(trs) > 1 and (trs[-2] in ENDINGQUOTE) and (trs[-1] == '.'):
            trs = trs[:-2]
        trs = trs.replace("()", "")
    except IndexError:  # s is  ''
        pass
    trs = trs.replace('...', ELLIPSIS)
    return trs


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
            '_'.join(TexSoup(langinfo.args[2].string).text or ['']),
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
    """
    FIXME: 123:
    \syacex{Noun}{Pronoun}{984}
    {ܗܲܝܡܵܢܘܼܬ݂ܹܗ}
    {haymānut-ēh}
    {faith-\poss.3\masc}
    {his faith}
    {\cite[70, \S 91e]{MuraokaSyriac}}
    """
    gll_start = re.compile(r'\\(g[l]{2,3}|exg\.|ag\.|bg\.)([^a-zA-Z]|$)')
    glt_start = re.compile(r'\\(glt|trans|Transl|TranslMulti|rede)([^a-zA-Z]|$)')
    longexampleandlanguage_pattern = re.compile(r'\\\\}{([^}]+)}$')

    linfo = None
    ex_pattern = re.compile(r"\\ex\s+(?P<lname>[A-Z][a-z]+)\s+(\([A-Z][0-9],\s+)?\\cite[^{]+{(?P<ref>[^}]+)}")
    gll, in_gll, prevline, pregll = [], False, None, None
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
                yield linfo[0] if linfo and (lineno - linfo[1] < 25) else None, gll, pregll
            gll, in_gll = [], False
            continue
        m = gll_start.search(line)
        if m:
            line = line[m.end() - 1:]
            gll, pregll = [], prevline
            in_gll = True
        if in_gll:
            gll.append(line)

        prevline = line


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
    comment = None

    # pre-process
    # Merge multi-word lexical glosses:
    multi_word_gloss = re.compile(r'(\s|^){([Ia-z ]+|North Wales|The birds)}(\s|,|$)')
    gl = multi_word_gloss.sub(
        lambda m: ' {} '.format(re.sub(r'\s+', '_', m.groups()[1])), gl).strip()
    gl = re.sub(r'(\s|^){}(\s|$)', ' _ ', gl.replace('{} {}', '{}  {}'))
    gl = re.sub(r'(\s|^){}{}(\s|$)', ' _ ', gl)
    gl = re.sub(r'(\s|^)~(\s|$)', ' _ ', gl)

    # Merge multi-word primary text groups:
    for k, v in {
        'Adnominal clause': '(Adnominal_clause)',
        'Adverbial clause': '(Adverbial_clause)',
        'Adverbila clause': '(Adverbial_clause)',

    }.items():
        pt = pt.replace(k, v)
    for k, v in CHAR_REPLS.items():
        pt = pt.replace(k, v)
    multi_word_pt = re.compile(r'(\s|^|-){([\w žąį./]+)}(\s|\.|$)')
    pt = multi_word_pt.sub(
        lambda m: ' {} '.format(re.sub(r'\s+', '_', m.groups()[1])), pt).strip()
    pt = re.sub(r'(\s|^){}(\s|$)', ' _ ', pt)

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
                comment.append(m.groups()[0])
                res = res[:-1]
            else:
                # A single word: Considered a comment.
                m = re.fullmatch(r'([\w]+)', to_text(res[-1].split('\n')[0])[0].strip())
                if m:
                    comment.append(m.groups()[0])
                    res = res[:-1]
                else:
                    # Language names appended as special comment in parentheses to the example.
                    m = re.fullmatch(r'\(?([A-Z][a-z]+(-English)?|[0-9/]+|[A-Z][A-Z]+)\)?', to_text(res[-1].split('\n')[0])[0].strip())
                    if m:
                        if m.groups()[0][0].isalpha() and m.groups()[0][0].islower():
                            linfo = (m.groups()[0], '', '')
                        else:
                            comment.append(m.groups()[0])
                        res = res[:-1]
    return [r.replace('\n', ' ') for r in res], '; '.join(comment), linfo


def get_title(s):
    from TexSoup import TexSoup
    for i, line in enumerate(s.split('\n')):
        try:
            ts = TexSoup(line, tolerance=1)
            if ts.chapter:
                return ' '.join(ts.chapter.text)
        except:
            pass
        if i > 5:
            return


def make_example(record, book, linfo, gll, prevline, filelanguage, gl_by_name, unknown_lgs):
    unknown_lgs = collections.Counter() if unknown_lgs is None else unknown_lgs
    _, _, refs = to_text(prevline)
    comment = []
    if linfo:
        linfo = [to_text(s or '')[0] for s in linfo]
        if linfo[2]:
            comment.append(linfo[2])
    #
    # Determine language:
    # 1. linfo
    # 2. chapter language
    # 3. book language
    #
    lname, glang = None, None
    if linfo:
        if linfo[0] not in gl_by_name:
            unknown_lgs.update([linfo[0]])
        else:
            lname = linfo[0]
            glang = gl_by_name[lname].id
    elif filelanguage:
        if filelanguage not in gl_by_name:
            unknown_lgs.update([filelanguage])
        else:
            lname = filelanguage
            glang = gl_by_name[lname].id
    elif record.language_glottocode:
        glang = record.language_glottocode
        lname = record.language_name

    #
    # At this point `gll` is just a bunch of text lines containing latex formatting.
    #
    # We assume the last text line to be the translation ...
    aligned, translation = '\n'.join(gll[:-1]), gll[-1]
    translation, cmt, _refs = to_text(translation)
    if _refs:
        refs.extend(_refs)
    if cmt:
        comment.append(cmt)

    # ... and split the remainder at latex newlines:
    aligned = [l.strip() for l in re.split(r'\\(?:\\|newline)', aligned) if l.strip()]

    # book-specifics:
    if record.id == 212:
        if len(aligned) > 2:
            if 'footnotesize' in aligned[2]:
                aligned = aligned[:2]

    aligned, cmt, linfo2 = lines_and_comment(aligned)
    if linfo2 and linfo2[0]:
        if linfo2[0] in gl_by_name:
            glang = gl_by_name[linfo2[0]].id
            lname = linfo2[0]
        else:
            unknown_lgs.update([linfo2[0]])
    # if glang:
    #    xx += 1
    if cmt:
        comment.append(cmt)

    al = []
    for l in aligned:
        delatexed, cmt, _refs = to_text(l)
        if _refs:
            refs.extend(_refs)
        if cmt:
            comment.append(cmt)
        if delatexed.replace('*', '').strip():
            al.append(l)
    aligned = al

    if len(aligned) == 3:
        # There's a separate line for the morpheme-segmented primary text!
        obj, pt, gl = aligned
    elif len(aligned) == 2:
        pt, gl = aligned
        obj = None
    elif len(aligned):
        if len(aligned) == 4 and aligned[3].startswith(r'}\\jambox'):
            obj, pt = aligned[0], aligned[1]
            gl = aligned[2] + aligned[3]
        else:  # Dunno what to do here ...
            # print(filename)
            # print(len(aligned), aligned)
            # print('---')
            return
    else:  # ... or here.
        return
    if obj:
        obj, cmt, _refs = to_text(obj)
        if _refs:
            refs.extend(_refs)
        if cmt:
            comment.append(cmt)

    pt, gl, cmt = fixed_alignment(pt, gl)
    if cmt:
        comment.append(cmt)
    nrefs = []
    if refs:
        for sid, pages in refs:
            if sid not in book.bib:
                # print(record.id, sid)
                comment.append('{}[{}]'.format(sid, pages))
            else:
                nrefs.append((book.bib[sid][0], pages))
    if len(pt) != len(gl):
        if gl and gl[-1] in ['()', '*()']:
            gl = gl[:-1]
    if len(pt) != len(gl):
        return

    return Example(
        TexDir=book,
        Primary_Text=obj,
        Analyzed_Word=pt,
        Gloss=gl,
        Translated_Text=translation,
        Language_ID=glang,
        Language_Name=lname,
        Comment=comment,
        Source=nrefs,
    )


@attr.s
class Example:
    # FIXME: yield obj text, segmented text, gloss, translation, language info, comment, refs
    TexDir = attr.ib()
    Primary_Text = attr.ib()
    Analyzed_Word = attr.ib(validator=attr.validators.instance_of(list))
    Gloss = attr.ib(validator=attr.validators.instance_of(list))
    Translated_Text = attr.ib(converter=clean_translation)
    Language_ID = attr.ib()
    Language_Name = attr.ib()
    Comment = attr.ib(converter=lambda s: '; '.join(s) or None)
    Source = attr.ib(validator=attr.validators.instance_of(list))
    IGT = attr.ib(default=None)
    ID = attr.ib(default=None)

    def __attrs_post_init__(self):
        from pyigt.igt import IGT

        self.IGT = IGT(
            phrase=self.Analyzed_Word,
            gloss=self.Gloss,
            translation=self.Translated_Text,
            abbrs=self.TexDir.abbreviations or {})
        assert self.IGT.is_valid(), str(self.IGT)
        if not self.Primary_Text:
            self.Primary_Text = self.IGT.primary_text
        self.ID = "{}-{}".format(self.TexDir.dir.name, hashlib.sha256(self.Primary_Text.replace('.', '').encode('utf8')).hexdigest()[:10])
        self.IGT.id = self.ID

    @property
    def coordination(self):
        for type_ in [' and ', ' or ']:
            if type_ in self.Translated_Text:
                return type_.strip()

    def _aspect(self, *types):
        for marker, type_ in types:
            if marker in self.Translated_Text.lower():
                return type_

    @property
    def time(self):
        return self._aspect((' yesterday ', 'past'), (' tomorrow ', 'future'), (' now ', 'present'))

    @property
    def modality(self):
        return self._aspect((' want ', 'volitive'))

    @property
    def polarity(self):
        return self._aspect((' not ', 'negative'))
