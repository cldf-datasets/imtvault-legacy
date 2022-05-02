"""
Language Science Press catalog records
"""
import attr


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
