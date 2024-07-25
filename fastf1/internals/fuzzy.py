import warnings

import numpy as np


with warnings.catch_warnings():
    warnings.filterwarnings(
        'ignore', message="Using slow pure-python SequenceMatcher"
    )
    # suppress that warning, it's confusing at best here, we don't need fast
    # sequence matching and the installation (on windows) requires some effort
    from rapidfuzz import fuzz


def fuzzy_matcher(
        query: str,
        reference: list[list[str]],
        abs_confidence: float = 0.0,
        rel_confidence: float = 0.0
) -> (int, bool):
    """
    Match a query string to a reference list of lists of strings using fuzzy
    string matching.

    The reference is a list of sub-lists where each sub-list represents one
    element. The sub-lists contain one or multiple feature strings. The idea is
    that each element can be described by multiple feature strings. The
    function tries to find the best matching element in the reference list
    for the given query string.

    The function first checks for exact substring matches with the individual
    feature strings. If there is exactly one sub-list, where the query
    is a substring of a feature string, this index is returned as an
    "accurate match". Else, the function uses fuzzy string matching to find the
    best match in the reference list. The index of the best matching element is
    then returned as an "inaccurate match".

    Args:
        query: The query string to match.
        reference: A list of lists where each sub-list contains one or multiple
            feature strings describing an element.
        abs_confidence: The minimum absolute confidence that the match must
            have when fuzzy matched. Must be a value between 0.0 and 1.0, where
              1.0 is equivalent to a perfect match. Set to 0.0 to disable.
              If the best match has a lower confidence, a KeyError is raised.
        rel_confidence: The minimum relative confidence that the match must
            have (compared with the second-best match). Must be a value greater
            than 0.0, where 0.5 would mean that the best match must have a 50%
            higher score than the second-best match. Set to 0.0 to disable.
            If the best match has a lower relative confidence, a KeyError is
            raised.

    Returns:
        (int, bool): Index of the best matching element in the
            reference (outer) list and a boolean indicating if the match is
            accurate or not.

    """
    # Preprocess the query and reference strings
    query = query.casefold().replace(" ", "")
    for i in range(len(reference)):
        for j in range(len(reference[i])):
            reference[i][j] = reference[i][j].casefold().replace(" ", "")

    # Check for exact substring matches with the individual feature strings
    # first. If there is exactly one reference tuple, where the query is a
    # substring of a feature string, return this index as accurate match.
    full_partial_match_indices = []
    for i, feature_strings in enumerate(reference):
        if any([query in val for val in feature_strings]):
            full_partial_match_indices.append(i)

    if len(full_partial_match_indices) == 1:
        # return index as accurate match
        return full_partial_match_indices[0], True

    # Zero or multiple reference tuples had substring matches, so we need to
    # do fuzzy matching
    reference = np.array(reference)
    ratios = np.zeros_like(reference, dtype=int)

    # If we have multiple substring matches, we only fuzzy match on these,
    # else we fuzzy match on all reference tuples
    if full_partial_match_indices:
        candidate_indices = full_partial_match_indices
    else:
        candidate_indices = range(len(reference))

    # Calculate the fuzz ratio for each feature string in each reference tuple
    for i in candidate_indices:
        feature_strings = reference[i]
        ratios[i] = [fuzz.ratio(val, query) for val in feature_strings]

    max_ratio = np.max(ratios)
    max_row_ratios = np.max(ratios, axis=1)
    # if there are multiple rows with the same maximum ratio, we need to remove
    # the corresponding ratios from the comparison so that we can match based
    # on the remaining feature string ratios
    if np.sum(max_row_ratios == max_ratio) > 1:
        # get counts of all unique ratios and remove all that are not unique
        # in the array by setting them to zero
        unique, counts = np.unique(reference, return_counts=True)
        count_dict = dict(zip(unique, counts))
        mask = ((np.vectorize(count_dict.get)(reference) > 1)
                & (ratios == max_ratio))
        ratios[mask] = 0

    # get the index of the row that contains the maximum ratio
    max_index = np.argmax(ratios) // ratios.shape[1]

    # optional confidence checks
    if abs_confidence and (max_ratio < (abs_confidence * 100)):
        raise KeyError(f"Found no match for '{query}' with sufficient "
                       f"absolute confidence")

    if rel_confidence and (max_ratio / np.partition(ratios.flatten(), -2)[-2]
                           < (1 + rel_confidence)):
        # max ratio divided by second-largest ratio is less
        # than 1 + rel_confidence
        raise KeyError(f"Found no match for '{query}' with sufficient "
                       f"relative confidence")

    # return index as inaccurate match
    return max_index, False
