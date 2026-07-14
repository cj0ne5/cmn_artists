from functools import lru_cache
from pathlib import Path

AGREEMENT_PATH = Path(__file__).resolve().parent / 'artist_agreement.txt'


@lru_cache(maxsize=1)
def get_artist_agreement_text():
    return AGREEMENT_PATH.read_text()
