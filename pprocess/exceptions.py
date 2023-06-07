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

class ExternalProcessException(Exception):
    """_summary_

    Args:
        Exception (_type_): _description_
    """

    def __init__(self):
        logger.error("Un suceso externo corto la ejecucion del procesador de tareas", exc_info=True)
        super().__init__("Un suceso externo corto la ejecucion del procesador de tareas")