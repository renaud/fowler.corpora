"""Implementation of Latent Semantic Analysis for dialogue act classification."""
import sys

import pandas as pd
import numpy as np

from sklearn.cross_validation import train_test_split
from sklearn.decomposition import TruncatedSVD
from sklearn.grid_search import GridSearchCV
from sklearn.metrics import precision_recall_fscore_support, accuracy_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.utils.multiclass import unique_labels

from fowler.corpora import io, util
from fowler.corpora.dispatcher import Dispatcher


def middleware_hook(kwargs, f_args):
    if kwargs['path'].endswith('.h5'):

        with pd.get_store(kwargs['path'], mode='r') as store:
            if 'cooccurrence_matrix' in f_args:
                kwargs['cooccurrence_matrix'] = io.load_cooccurrence_matrix(store)

            if 'labels' in f_args:
                kwargs['labels'] = io.load_labels(store)

            if 'store_metadata' in f_args:
                kwargs['store_metadata'] = store.get_storer('data').attrs.metadata

    if 'path' not in f_args:
        del kwargs['path']


dispatcher = Dispatcher(
    middleware_hook=middleware_hook,
    globaloptions=(
        ('p', 'path', 'out.h5', 'The path to the store hd5 file.'),
    ),
)
command = dispatcher.command


@command()
def plain_lsa(
    cooccurrence_matrix,
    labels,
    templates_env,
    store_metadata,
    n_jobs=('j', -1, 'The number of CPUs to use to do computations. -1 means all CPUs.'),
    n_folds=('f', 10, 'The number of folds used for cross validation.'),
):
    """Perform the Plain LSA method."""
    X_train, X_test, y_train, y_test = train_test_split(
        cooccurrence_matrix.T,
        labels,
        test_size=0.5,
        random_state=0,
    )

    tuned_parameters = {
        'nn__n_neighbors': (1, 5),
    }

    pipeline = Pipeline(
        [
            ('svd', TruncatedSVD(n_components=50)),
            ('nn', KNeighborsClassifier()),
        ]
    )

    clf = GridSearchCV(
        pipeline,
        tuned_parameters,
        cv=n_folds,
        scoring='accuracy',
        n_jobs=n_jobs,
    )
    clf.fit(X_train, y_train)
    y_predicted = clf.predict(X_test)
    prfs = precision_recall_fscore_support(y_test, y_predicted)

    util.display(
        templates_env.get_template('classification_report.rst').render(
            argv=' '.join(sys.argv) if not util.inside_ipython() else 'ipython',
            paper='Serafin et al. 2003',
            clf=clf,
            tprfs=zip(unique_labels(y_test, y_predicted), *prfs),
            p_avg=np.average(prfs[0], weights=prfs[3]),
            r_avg=np.average(prfs[1], weights=prfs[3]),
            f_avg=np.average(prfs[2], weights=prfs[3]),
            s_sum=np.sum(prfs[3]),
            store_metadata=store_metadata,
            accuracy=accuracy_score(y_test, y_predicted),
        )
    )
