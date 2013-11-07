import numpy as np

from fowler.corpora.serafim03.classifier import PlainLSA

import pytest


@pytest.fixture
def word_document_matrix():
    """A small word-document matrix that represents a toy dialog.

    The 6 utterances (documents) are::

        - How are you?
        - I am fine, thank you.
        - Are you OK?
        - Yes, I am.
        - Am I OK?
        - No, you are not.

    Punctuation is ignored. Rows in the matrix correspond to the words,
    collumns to the documents.

    """
    return np.matrix((
        (1, 0, 0, 0, 0, 0),  # how
        (1, 0, 1, 0, 0, 1),  # are
        (1, 1, 1, 0, 0, 1),  # you
        (0, 1, 0, 1, 1, 0),  # i
        (0, 1, 0, 1, 1, 0),  # am
        (0, 1, 0, 0, 0, 0),  # fine
        (0, 1, 0, 0, 0, 0),  # thank
        (0, 0, 1, 0, 1, 0),  # ok
        (0, 0, 0, 1, 0, 0),  # yes
        (0, 0, 0, 0, 0, 1),  # no
        (0, 0, 0, 0, 0, 1),  # not
    ))


@pytest.fixture
def y():
    """The tags for the toy dialog."""
    return np.array(list('012345'))


@pytest.mark.parametrize(
    ('vector', 'expected_labels'),
    (
        # How are you?
        (
            np.array([[1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0]]),
            np.array(['0']),
        ),
        # I am fine, thank you.
        (
            np.array([[0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0]]),
            np.array(['1']),
        ),
        # I am *OK*, thank you.
        (
            np.array([[0, 0, 1, 1, 1, 0, 1, 1, 0, 0, 0]]),
            np.array(['1']),
        ),
        (
            np.array([
                [1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0],
                [0, 0, 1, 1, 1, 0, 1, 1, 0, 0, 0],
            ]),
            np.array(['0', '1', '1']),
        ),
    ),
)
def test_plainlsa(word_document_matrix, y, vector, expected_labels):
    cl = PlainLSA(2)
    cl.fit(word_document_matrix, y)
    labels = cl.predict(vector)

    assert (labels == expected_labels).all()
