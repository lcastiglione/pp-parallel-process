"""
Módulo que contiene los tipos de excepciones que pueden ocurrir en el método de conexión con Redis.
"""
from logs.logger import logger


class ResponseProcessException(Exception):
    """_summary_

    Args:
        Exception (_type_): _description_
    """

    def __init__(self, msg):
        logger.error("Se produjo un error al procesar la tarea: %s", msg, exc_info=True)
        super().__init__(f"Se produjo un error al procesar la tarea: {msg}")

class UserProcessException(Exception):
    """_summary_

    Args:
        Exception (_type_): _description_
    """

    def __init__(self):
        logger.error("Se corto la ejecucion de la tarea", exc_info=True)
        super().__init__("Se corto la ejecucion de la tarea")