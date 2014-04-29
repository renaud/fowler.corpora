"""Access to the BNC corpus.

You can obtain the full version of the BNC corpus at
http://www.ota.ox.ac.uk/desc/2554

"""
import logging
from collections import Counter
from itertools import chain

from more_itertools import chunked

import pandas as pd
from nltk.corpus.reader.bnc import BNCCorpusReader

from fowler.corpora.dispatcher import Dispatcher, Resource, NewSpaceCreationMixin, DictionaryMixin
from fowler.corpora.space.util import write_space
from .util import count_cooccurrence


logger = logging.getLogger(__name__)


class BNCDispatcher(Dispatcher, NewSpaceCreationMixin, DictionaryMixin):
    """BNC dispathcer."""

    global__bnc = '', 'corpora/BNC/Texts', 'Path to the BNC corpus.'
    global__fileids = '', r'[A-K]/\w*/\w*\.xml', 'Files to be read in the corpus.'

    @Resource
    def bnc(self):
        """BNC corpus reader."""
        root = self.kwargs['bnc']
        return BNCCorpusReader(root=root, fileids=self.fileids)


dispatcher = BNCDispatcher()
command = dispatcher.command


def bnc_cooccurrence(args):
    """Count word couccurrence in a BNC file."""
    root, fileids, window_size, stem, targets, context = args

    logger.debug('Processing %s', fileids)

    cooccurences = count_cooccurrence(
        BNCCorpusReader(root=root, fileids=fileids).tagged_words(stem=stem),
        window_size=window_size,
    )

    if not isinstance(targets.index[0], tuple):
        cooccurences = ((t[0], c, n)for t, c, n in cooccurences)

    counts = Counter(
        dict(
            ((targets.loc[t].id, context.loc[c].id), n)
            for t, c, n in cooccurences
            if (t in targets.index) and (c in context.index)
        )
    )

    return counts


def do_sum_counters(args):
    if len(args) == 1:
        return args[0]

    logger.debug('Summing up %d counters.', len(args))
    return sum(args, Counter())


def sum_counters(counters, pool, chunk_size=7):
    while True:
        counters = chunked(counters, chunk_size)

        first = next(counters)
        if len(first) == 1:
            logger.debug('Got results for a chunk.')
            return first[0]

        counters = pool.imap_unordered(do_sum_counters, chain([first], counters))


@command()
def cooccurrence(
    bnc,
    pool,
    targets,
    context,
    window_size=('', 5, 'Window size.'),
    chunk_size=('', 7, 'Length of the chunk at the reduce stage.'),
    stem=('', False, 'Use word stems instead of word strings.'),
    output=('o', 'matrix.h5', 'The output matrix file.'),
):
    """Build the co-occurrence matrix."""
    records = Counter()

    for fileids_chunk in chunked(bnc.fileids(), 100):

        counters = pool.imap_unordered(
            bnc_cooccurrence,
            (
                (bnc.root, fileids, window_size, stem, targets, context)
                for fileids in fileids_chunk
            ),
        )

        records += sum_counters(counters, pool=pool, chunk_size=chunk_size)

        logger.debug('There are %d co-occurrence records so far.', len(records))

    matrix = pd.DataFrame(
        ([t, c, n] for (t, c), n in records.items()),
        columns=('id_target', 'id_context', 'count'),
    )
    matrix.set_index(['id_target', 'id_context'], inplace=True)

    write_space(output, context, targets, matrix)


def bnc_words(args):
    root, fileids, c5, stem, omit_tags = args
    logger.debug('Processing %s', fileids)
    bnc = BNCCorpusReader(root=root, fileids=fileids)

    try:
        if not omit_tags:
            return Counter(bnc.tagged_words(stem=stem, c5=c5))
        else:
            return Counter(bnc.words(stem=stem))
    except:
        logger.error('Could not process %s', fileids)
        raise


@command()
def dictionary(
    bnc,
    pool,
    dictionary_key,
    output=('o', 'dicitionary.h5', 'The output file.'),
    c5=('', False, 'Use more detailed c5 tags.'),
    stem=('', False, 'Use word stems instead of word strings.'),
    omit_tags=('', False, 'Do not use POS tags.'),
):
    """Extract word frequencies from the corpus."""
    words = sum_counters(
        pool.imap_unordered(
            bnc_words,
            ((bnc.root, fid, c5, stem, omit_tags) for fid in bnc.fileids()),
        ),
        pool=pool,
    )

    logger.debug('The final counter contains %d items.', len(words))

    if not omit_tags:
        words = ([w, t, c] for (w, t), c in words.items())
        columns = 'ngram', 'tag', 'count'
    else:
        words = ([w, c] for w, c in words.items())
        columns = 'ngram', 'count'

    (
        pd.DataFrame(words, columns=columns)
        .sort('count', ascending=False)
        .to_hdf(
            output,
            dictionary_key,
            mode='w',
            complevel=9,
            complib='zlib',
        )
    )
