import itertools
from typing import TypeVar, Iterable, Iterator, Tuple, Optional

T = TypeVar('T')


def window(iterator: Iterable[T], behind: int = 0, ahead: int = 0) -> Iterator[Tuple[Optional[T], ...]]:
    """
    Sliding window for an iterator.

    Example:
        >>> for prev, i, nxt in window(range(10), 1, 1):
        >>>     print(prev, i, nxt)

        None 0 1
        0 1 2
        1 2 3
        2 3 None
    """
    # TODO: move into utils
    iters = list(itertools.tee(iterator, behind + 1 + ahead))
    for i in range(behind):
        iters[i] = itertools.chain((behind - i) * [None], iters[i])
    for i in range(ahead):
        iters[-1 - i] = itertools.islice(
            itertools.chain(iters[-1 - i], (ahead - i) * [None]),
            (ahead - i),
            None
        )
    return zip(*iters)
