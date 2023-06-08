"""
Módulo que contiene los tipos de excepciones que pueden ocurrir en el método de conexión con Redis.
"""


class ResponseProcessException(Exception):
    """_summary_

    Args:
        Exception (_type_): _description_
    """

    def __init__(self, msg):
        super().__init__(f"Se produjo un error al procesar la tarea: {msg}")


class ExternalProcessException(Exception):
    """_summary_

    Args:
        Exception (_type_): _description_
    """

    def __init__(self):
        super().__init__("Un suceso externo corto la ejecucion del procesador de tareas")
