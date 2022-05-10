import re
import math
import pathlib
import collections

from tqdm import tqdm
from pyigt.igt import LGRConformance
from cldfbench import Dataset as BaseDataset
from pycldf.sources import Reference
from csvw.metadata import URITemplate
import linglit
from linglit.bibtex import iter_merged


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "imtvault"

    def cldf_specs(self):  # A dataset must declare all CLDF sets it creates.
        return super().cldf_specs()

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

        args.writer.objects['LanguageTable'].append(dict(
            ID='undefined',
            Name='Undefined Language',
        ))

        sources, langs = {}, set()
        lgs, contribs = collections.Counter(), collections.Counter()
        for pub in tqdm(linglit.iter_publications(
                '../../cldf/linglit', glottolog=args.glottolog.api, with_examples=True)):
            args.writer.objects['ContributionTable'].append(dict(
                ID=pub.id,
                Name=pub.record.title,
                Contributor=pub.record.creators,
                Citation=str(pub.as_source()),
            ))
            for ex in pub.examples:
                if ex.Language_ID and ex.Language_ID not in langs:
                    ml = args.glottolog.api.cached_languoids[ex.Language_ID]
                    args.writer.objects['LanguageTable'].append(dict(
                        ID=ml.id,
                        Name=ml.name,
                        Glottocode=ml.id,
                        Latitude=ml.latitude,
                        Longitude=ml.longitude,
                    ))
                    langs.add(ex.Language_ID)
                if ex.Meta_Language_ID and ex.Meta_Language_ID not in langs:
                    ml = args.glottolog.api.cached_languoids[ex.Meta_Language_ID]
                    args.writer.objects['LanguageTable'].append(dict(
                        ID=ml.id,
                        Name=ml.name,
                        Glottocode=ml.id,
                        Latitude=ml.latitude,
                        Longitude=ml.longitude,
                    ))
                    langs.add(ex.Meta_Language_ID)
                igt = ex.as_igt()
                args.writer.objects['ExampleTable'].append(dict(
                    ID=ex.ID,
                    Language_ID=ex.Language_ID or 'undefined',
                    Language_Name=ex.Language_Name,
                    Meta_Language_ID=ex.Meta_Language_ID,
                    Primary_Text=ex.Primary_Text,
                    Analyzed_Word=ex.Analyzed_Word,
                    Gloss=ex.Gloss,
                    Translated_Text=ex.Translated_Text,
                    LGR_Conformance_Level=str(igt.conformance),
                    Abbreviations=igt.gloss_abbrs if igt.conformance == LGRConformance.MORPHEME_ALIGNED else {},
                    Source=[Reference(k, (v or '').replace(';', ',')) for k, v in ex.Source],
                    Comment=ex.Comment,
                    Contribution_ID=pub.id,
                ))
                contribs.update([pub.id])
                lgs.update([ex.Language_ID])
                for src in pub.example_sources(ex):
                    sources[src.id] = src
            #if len(args.writer.objects['ExampleTable']) > 1000:
            #    break

        bibkey_map = {}
        entries = []
        for src in sources.values():
            e = src.entry
            e.key = src.id
            entries.append(e)
        for src, keymap in iter_merged(entries):
            bibkey_map.update(keymap)
            args.writer.cldf.sources.add(src)

        for ex in args.writer.objects['ExampleTable']:
            refs = []
            for ref in ex['Source']:
                ref.source = bibkey_map[ref.source]
                refs.append(str(ref))
            ex['Source'] = refs

        for lg in args.writer.objects['LanguageTable']:
            if lg['ID'] != 'undefined':
                lg['Examples_Count'] = lgs.get(lg['ID'], 0)
                lg['Examples_Count_Log'] = math.log(lgs.get(lg['ID'], 1))
        for c in args.writer.objects['ContributionTable']:
            c['Examples_Count'] = contribs[c['ID']]
