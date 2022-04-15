import re
import logging
import functools

from clldutils import lgr
from pylatexenc import latexwalker, latex2text, macrospec
from pyigt.igt import NON_OVERT_ELEMENT

SIMPLE_MACROS = {
    'Tilde': '~',
    'oneS': '1S',
    'twoS': '2S',
    'oneP': '1P',
    'twoP': '2P',
    'CL': 'CL',
    'ob': '[',
    'cb': ']',
    'op': '(',
    'cp': ')',
    'db': ' [',
    'R': 'r',
    'Nonpast': 'NONPAST',
    'redp': '~',
    'Stpl': '2|3PL',
    'Masc': 'MASC',
    'PSP': 'PSP',
    'Fsg': '1SG',
    'Fpl': '1PL',
    'ATT': 'ATT',
    'deff': 'DEFF',
    'Ssg': '2SG',
    'Stsg': '2|3SG',
    'Third': '3',
    'Tsg': '3SG',
    'IFV': 'IFV',
    'Second': '2',
    'Aand': '&',
    'IO': 'IO',
    'Io': 'IO',
    'LINK': 'LINK',
    'flobv': '→3',
    'fl': '→',
    'Venit': 'VENT',
    'Ndu': 'NDU',
    'PN': 'PN',
    'slash': '/',
    'DEP': 'DEP',
    'USSmaller': '<',
    'USGreater': '>',
    'defn': 'DEFN',
    'Char': 'CHAR',
    'DO': 'DO',
    'Rpst': 'RPST',
    'Ext': 'EXT',
    'EXT': 'EXT',
    'shin': 'ʃ',
    'shinB': 'ʃ',
    'alef': 'ʔ',
    'alefB': 'ʔ',
    'ayin': 'ʕ',
    'ayinB': 'ʕ',
    'het': 'ħ',
    'hetB': 'ħ',
    'PRON': 'PRON',
    'NOUN': 'NOUN',
    'CONJ': 'CONJ',
    'glossF': 'F',
    'glsg': 'SG',
    'INSTR': 'INSTR',
    'POT': 'POT',
    'PLU': 'PLU',
    'RETRO': 'RETRO',
    'CONTR': 'CONTR',
    'USOParen': '(',
    'USCParen': ')',
    'conn': 'CONN',
    'At': 'AT',
    'textepsilon': 'ɛ',
    'textopeno': 'ɔ',
    'textbeltl': 'ɬ',
    'textless': '<',
    'textgreater': '>',
    'textltailn': 'ɲ',
    'textquotedbl': '"',
    'textsci': 'ɪ',
    'IDPH': 'IDPH',
    'MOD': 'MOD',
    'Aor': 'AOR',
    'glossINF': 'INF',
    'Subj': 'SUBJ',
    'abi': 'ABI',
    'hest': 'HEST',
    'quant': 'QUANT',
    'RECIP': 'RECIP',
    'USEmptySet': '∅',
    'Obl': 'OBL',
    'Indic': 'INDIC',
    'Dei': 'DEI',
    'Expl': 'EXPL',
    'Sdu': 'SDU',
    'Mid': 'MID',
    'Npst': 'NPST',
    'Nom': 'NOM',
    'Nw': 'NW',
    'Act': 'ACT',
    'textgamma': 'ɣ',
    'textperiodcentered': '·',
    'cras': 'CRAS',
    'PRIOR': 'PRIOR',
    'SIM': 'SIM',
    'Lnk': 'LNK',
    'Av': 'AV',
    'Ppp': 'PPP',
    'Futimp': 'FUTIMP',
    'deter': 'DETER',
    'mut': 'MUT',
    'NC': 'NC',
    'textglotstop': 'ʔ',
    'textraiseglotstop': 'ʔ',
    'Intj': 'INTJ',
    'Prt': 'PRT',
    'NEUT': 'NEUT',
    'PF': 'PF',
    'z': '',
    'expl': 'EXPL',
    'Emph': 'EMPH',
    'Hab': 'HAB',
    'Gam': 'GAM',
    'Vc': 'VC',
    'Stnsg': '2|3NSG',
    'Only': 'ONLY',
    'Imn': 'IMN',
    'Rs': 'RS',
    'Recog': 'RECOG',
    'Iam': 'IAM',
    'Prop': 'PROP',
    'Betaone': 'Β1',
    'Betatwo': 'Β2',
    'Appr': 'APPR',
    'Bet': 'Β',
    'Pot': 'POT',
    'Imm': 'IMM',
    'Immpst': 'IPST',
    'Fnsg': '1NSG',
    'Dim': 'DIM',
    'Med': 'MED',
    'Stat': 'STAT',
    'Zero': NON_OVERT_ELEMENT,
    'Lk': 'LK',
    'Alph': 'Α',
    'reln': 'RELN',
    'postp': 'POSTP',
    'dxm': 'DXM',
    'ideo': 'IDEO',
    'ident': 'IDENT',
    'psg': 'PSG',
    'mod': 'MOD',
    'itr': 'ITR',
    'hab': 'HAB',
    'egr': 'EGR',
    'qual': 'QUAL',
    'la': 'lá',
    'baru': 'ʉ',
    'baruL': 'ʉ̀',
    'baruH': 'ʉ́',
    'ep': 'ε',
    'epL': 'ὲ',
    'epH': 'έ',
    'schwa': 'ə',
    'schwaH': 'ə́',
    'schwaL': 'ə̀',
    'mbuHL': 'mbʉ́ʉ̀',
    'mbuLH': 'mbʉ̀ʉ́',
    'mbuL': 'mb̀ʉ̀',
    'oo': 'ɔ',
    'ooH': 'ɔ́',
    'ooL': 'ɔ̀',
    'nda': 'ndà',
    'longrule': '_',
    'cmpr': 'CMPR',
    'thestrong': 'the',
    'theweak': 'the',
    'emphat': 'EMPH',
    'pstpunc': 'PSTPUNC',
    'relativ': 'REL',
    'cert': 'CERT',
    'att': 'ATT',
    'antip': 'ANTIP',
    'prep': 'PREP',
    'partic': 'PART',
    'antgen': 'ANTGEN',
    'am': 'AM',
    'asp': 'ASP',
    'ideoph': 'IDEOPH',
    'prosp': 'PROSP',
    'pstrem': 'PSTREM',
    'fem': 'F',
    'mas': 'M',
    'faff': 'FAFF',
    'intens': 'INTENS',
    ':': 'ː',
    'fin': 'FIN',
    'conj': 'CONJ',
    'allo': 'ALLO',
    'ines': 'INES',
    'icml': 'ICML',
    'tns': 'TNS',
    'uop': 'UOP',
    'Hyp': 'HYP',
    'dsbj': 'DSBJ',
    'topic': 'TOP',
    'dir': 'DIR',
    'cs': 'CS',
    'question': 'Q',
    'glopa': 'OPA',
    'glme': 'TOP',
    'glte': 'NFIN',
    'glta': 'NFIN',
    'Cl': 'CL',
    'Rci': 'RCI',
    'Spl': '2PL',
    'Sm': 'SM',
    'Fv': 'FV',
    'Aug': 'AUG',
    'Dj': 'DJ',
    'Om': 'OM',
    'glossQ': 'Q',
    'Depend': 'DEPEND',
    'Simp': 'SIMP',
    'Vn': 'VN',
    'Asp': 'ASP',
    'Invol': 'INVOL',
    'Volition': 'volition',
    'sVP': 'VP',
}

logging.getLogger('pylatexenc.latexwalker').setLevel(logging.WARNING)

#
# Define macros, environments, specials for the *parser*
#
# FIMXE: parse citations!
#
macros = [
    macrospec.MacroSpec("footnotetext", "{"),
    macrospec.MacroSpec("footnote", "{"),
    macrospec.MacroSpec("japhdoi", "{"),
    macrospec.MacroSpec("textup", "{"),
    macrospec.MacroSpec("tss", "{"),
    macrospec.MacroSpec("ili", "{"),
    macrospec.MacroSpec("llap", "{"),
    macrospec.MacroSpec("textsc", "{"),
    macrospec.MacroSpec("tsc", "{"),
    macrospec.MacroSpec("gsc", "{"),
    macrospec.MacroSpec("ig", "{"),
    macrospec.MacroSpec("ulp", "{{"),
    macrospec.MacroSpec("japhug", "{{"),
    macrospec.MacroSpec("gloss", "{"),
    macrospec.MacroSpec("REF", "{"),
    macrospec.MacroSpec("mc", "{"),
    macrospec.MacroSpec("particle", "{"),
    macrospec.MacroSpec("jambox", "[{"),
]
for k in SIMPLE_MACROS:
    macros.append(macrospec.MacroSpec(k, ""))
for abbr in lgr.ABBRS:
    if abbr:
        macros.extend([
            macrospec.MacroSpec(abbr, ""),
            macrospec.MacroSpec(abbr.lower(), ""),
        ])
        if len(abbr) > 1:
            macros.append(macrospec.MacroSpec(abbr.capitalize(), ""))

lw_context_db = latexwalker.get_default_latex_context_db()
lw_context_db.add_context_category('gll', prepend=True, macros=macros[:])

#
# Implement macros, environments, specials for the *conversion to text*
#

def uppercase_arg(n, l2tobj):
    return l2tobj.nodelist_to_text([n.nodeargd.argnlist[0]]).upper()


def dot_uppercase_arg(n, l2tobj):
    return '.' + l2tobj.nodelist_to_text([n.nodeargd.argnlist[0]]).upper()


def footnote(n, l2tobj):
    return "<fn>{}</fn>".format(l2tobj.nodelist_to_text([n.nodeargd.argnlist[0]]).replace('<', '&lt;'))


def japhdoi(n, l2tobj):
    return '<a href="https://doi.org/10.24397/pangloss-{}"></fn>'.format(
        l2tobj.nodelist_to_text([n.nodeargd.argnlist[0]]))


def firstarg(n, l2tobj):
    return l2tobj.nodelist_to_text([n.nodeargd.argnlist[0]])


def repl(abbr, *args):
    return abbr


def japhug(n, l2tobj):
    return "{} [{}]".format(
        l2tobj.nodelist_to_text([n.nodeargd.argnlist[0]]),
        l2tobj.nodelist_to_text([n.nodeargd.argnlist[1]]),
    )


macros = [
    latex2text.MacroTextSpec("footnote", simplify_repl=footnote),
    latex2text.MacroTextSpec("footnotetext", simplify_repl=footnote),
    latex2text.MacroTextSpec("japhdoi", simplify_repl=japhdoi),
    latex2text.MacroTextSpec("japhug", simplify_repl=japhug),
    latex2text.MacroTextSpec("textup", simplify_repl=firstarg),
    latex2text.MacroTextSpec("ulp", simplify_repl=firstarg),
    latex2text.MacroTextSpec("textsc", simplify_repl=uppercase_arg),
    latex2text.MacroTextSpec("tsc", simplify_repl=uppercase_arg),
    latex2text.MacroTextSpec("tss", simplify_repl=dot_uppercase_arg),
    latex2text.MacroTextSpec("gsc", simplify_repl=uppercase_arg),
    latex2text.MacroTextSpec("ig", simplify_repl=uppercase_arg),
    latex2text.MacroTextSpec("mc", simplify_repl=uppercase_arg),
    latex2text.MacroTextSpec("gloss", simplify_repl=uppercase_arg),
    latex2text.MacroTextSpec("llap", simplify_repl=lambda *args: ''),
    #latex2text.MacroTextSpec("ili", simplify_repl=lambda *args: ''),
    latex2text.MacroTextSpec("ili", simplify_repl=firstarg),
    latex2text.MacroTextSpec("REF", simplify_repl=lambda *args: ''),
    latex2text.MacroTextSpec("particle", simplify_repl='PARTICLE'),
    latex2text.MacroTextSpec("jambox", simplify_repl=''),
]
for k, v in SIMPLE_MACROS.items():
    macros.append(latex2text.MacroTextSpec(k, simplify_repl=functools.partial(repl, v)),)
for abbr in lgr.ABBRS:
    if abbr:
        macros.extend([
            latex2text.MacroTextSpec(abbr, simplify_repl=functools.partial(repl, abbr)),
            latex2text.MacroTextSpec(abbr.lower(), simplify_repl=functools.partial(repl, abbr)),
        ])
        if len(abbr) > 1:
            macros.append(
                latex2text.MacroTextSpec(abbr.capitalize(), simplify_repl=functools.partial(repl, abbr)))

l2t_context_db = latex2text.get_default_latex_context_db()
l2t_context_db.add_context_category('gll', prepend=True, macros=macros[:])


#
# Here is an example usage:
#

def custom_latex_to_text(input_latex):
    # the latex parser instance with custom latex_context
    lw_obj = latexwalker.LatexWalker(input_latex, latex_context=lw_context_db)
    # parse to node list
    nodelist, pos, length = lw_obj.get_latex_nodes()
    # initialize the converter to text with custom latex_context
    l2t_obj = latex2text.LatexNodes2Text(latex_context=l2t_context_db)
    # convert to text
    try:
        return l2t_obj.nodelist_to_text(nodelist)
    except IndexError:
        print('+++', input_latex)
        return input_latex


def to_text(latex, mode='primary_text'):
    latex = latex.replace(r'{\sc ', r'\textsc{')
    latex = latex.replace(r'{\scshape ', r'\textsc{')
    text, comment = custom_latex_to_text(latex), None
    text = text.strip()
    # extract footnotes:
    fn_pattern = re.compile(r'<fn>([^<]+)</fn>')
    m = fn_pattern.search(text)
    if m:
        comment = m.groups()[0]
        text = fn_pattern.sub('', text).strip()

    #
    # FIXME: handle *\textit commands
    #

    #text = re.sub(r'\s+\[\s+', ' [', text)
    #text = re.sub(r'\s+]\s+', '] ', text)

    if mode == 'primary_text':
        return text, comment
    if mode == 'gloss':
        return text, comment
    if mode == 'translation':
        #
        # FIXME:
        # - extract \footnote into comment!
        # - remove <cit.> added for citations
        # - remove quotes
        #
        return text, comment
