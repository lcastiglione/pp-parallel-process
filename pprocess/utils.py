"""Funciones utils del proyecto"""

import uuid


def get_uid() -> str:
    """Genera un id único

    Returns:
        (str): id único
    """
    return str(uuid.uuid4())
