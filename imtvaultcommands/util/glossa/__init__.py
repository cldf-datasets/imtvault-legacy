import re
import collections

import attr
from lxml.etree import fromstring
from pycldf.sources import Source

from . import parse
from imtvaultcommands.util.extractgll import clean_translation

GC_PATTERN = re.compile(r'[a-z0-9]{4}[0-9]{4}')


class LanguageSpec:
    def __init__(self, spec, gl_by_name):
        self.gl_by_name = gl_by_name
        self.language_ranges = {}
        self.language = None
        if spec.strip():
            chunks = [s.strip() for s in spec.split(',')]
            if len(chunks) == 1 and GC_PATTERN.fullmatch(chunks[0]):
                self.language = chunks[0]
            elif chunks:
                for chunk in chunks:
                    glottocode, _, range = chunk.partition(':')
                    glottocode = glottocode.strip()
                    assert GC_PATTERN.fullmatch(glottocode)
                    lower, _, upper = range.partition('-')
                    lower = int(lower) if lower.strip() else 0
                    upper = int(upper) if upper.strip() else 1000
                    self.language_ranges[glottocode] = (lower, upper)

    def __call__(self, ex):
        # 1. Check, if ex has already a resolvable Language_Name
        if ex.Language_Name:
            if ex.Language_Name in self.gl_by_name:
                return self.gl_by_name[ex.Language_Name].id
            ex.Language_Name = None
            return
        if self.language:
            return self.language
        if self.language_ranges:
            # Get the numeric part of the local ID
            m = re.match(r'[0-9]+', ex.Local_ID)
            if m:
                lid = int(ex.Local_ID[:m.end()])
                for gc, (min, max) in self.language_ranges.items():
                    if min <= lid <= max:
                        return gc


@attr.s
class Example:
    Primary_Text = attr.ib()
    Analyzed_Word = attr.ib(validator=attr.validators.instance_of(list))
    Gloss = attr.ib(validator=attr.validators.instance_of(list))
    Translated_Text = attr.ib(converter=lambda s: clean_translation(s) if s else None)
    Language_ID = attr.ib()
    Language_Name = attr.ib()
    Comment = attr.ib()
    Source = attr.ib(validator=attr.validators.instance_of(list))
    IGT = attr.ib()
    ID = attr.ib()
    Local_ID = attr.ib()


@attr.s
class Article:
    record = attr.ib(validator=attr.validators.instance_of(Source))
    refs = attr.ib(validator=attr.validators.instance_of(dict))
    abbreviations = attr.ib(validator=attr.validators.instance_of(dict))
    doc = attr.ib()

    def __attrs_post_init__(self):
        refs = collections.OrderedDict()
        for v in self.refs.values():
            v.id = '{}_{}'.format(self.record.id, v.id)
            refs[v.id] = v
        self.refs = refs

    @classmethod
    def from_doc(cls, p):
        doc = fromstring(p.read_bytes().replace(b'&nbsp;', b'&#160;'))
        return cls(
            doc=doc,
            record=parse.metadata(p, doc),
            refs=collections.OrderedDict([(s.id, s) for s in parse.refs(doc)]),
            abbreviations=parse.abbreviations(doc),
        )

    def iter_igt(self):
        for count, number, letter, lang, xrefs, igt in parse.iter_igt(self.doc, self.abbreviations):
            lid = '{}{}'.format(number or '', letter or '')
            refs = []
            for sid, reft, label in xrefs:
                if reft == 'bibr':
                    sid = '{}_{}'.format(self.record.id, sid)
                    pages = label.partition(':')[2].strip() if label else ''
                    refs.append((sid, pages.replace('[', '(').replace(']', ')')))
            if refs:
                refs.append((self.record.id, 'via:{}'.format(lid)))
            else:
                refs.append((self.record.id, lid))
            yield Example(
                ID='{}-{}'.format(self.record.id, count),
                Local_ID=lid,
                Primary_Text=igt.primary_text,
                Analyzed_Word=igt.phrase,
                Gloss=igt.gloss,
                Translated_Text=igt.translation,
                Language_ID=None,
                Language_Name=lang,
                Comment=None,
                Source=refs,
                IGT=igt,
            )
