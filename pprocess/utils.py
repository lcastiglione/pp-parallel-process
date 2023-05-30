"""Funciones utils del proyecto"""

from itertools import islice
from typing import List
import uuid


def get_uid() -> str:
    """Genera un id único

    Returns:
        (str): id único
    """
    return str(uuid.uuid4())


def find_small_missing_number(list_n: List[int]):
    """Funión que busca y devuelve el número más chico que falta en una lista de números.

    Args:
        list_n (List[int]): Lista de números.

    Returns:
        _type_: Número faltante
    """
    set_n = set(sorted(list_n))  # Convertir la lista en un conjunto

    # Buscar el número más pequeño que falta en el rango de valores
    for i in range(len(list_n) + 1):
        if i not in set_n:
            return i


def split_array(array, n):
    iter_array = iter(array)
    return list(iter(lambda: list(islice(iter_array, n)), []))
