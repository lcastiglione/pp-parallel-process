"""Funciones utils del proyecto"""

from typing import Any, List
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


def split_array(array: List[Any], chunk: int) -> List[List[Any]]:
    """Devide un array en 'n' arrays.

    Args:
        array (List[Any]): Array a dividir
        n (int): Cantidad de subarrays requeridos

    Returns:
        List[List[Any]]: Array con los subarrays adentro
    """
    return [array[i:i + chunk] for i in range(0, len(array), chunk)]
