"""
Módulo encargado de definir las funciones para ejecutar un análisis de performance
"""
from datetime import datetime
import json
from typing import List, Dict

from pprocess.utils.utils import get_uid

config = {
    'status': False,
    'data': {}
}


def activate_performance() -> None:
    """Activa el análisis de performance. Esto activa el registro de todos los checkpoints que están en el código.
    """
    config['status'] = True


def checkpoint(description: str=None, check_id: str = None) -> str | None:
    """Crear un checkpoint indicando un id, tiempo y descripción.

    Args:
        description (_type_): Descripción del checkpoint
        last_check_id (str, optional): ID de un checkpoint anterior. Por default es None.
    """
    if config['status']:
        check_id = check_id if check_id else get_uid()
        if check_id not in config['data']:
            config['data'][check_id] = {
                'time': datetime.now(),
                'description': description
            }
        else:
            config['data'][check_id] = {
                'start': config['data'][check_id]['time'],
                'end': datetime.now(),
                'description': config['data'][check_id]['description']
            }
        return check_id


def clean_performance_data() -> None:
    """Se limpia el buffer de memoria donde están los checkpoints
    """
    config['data'] = {}


def get_total_time(values: List[Dict]) -> float:
    """Calcula el tiempo total desde el inicio hasta el final del análisis de rendimiento.

    Returns:
        float: Tiempo en milisegundos
    """
    start = values[0]['time'] if 'time' in values[0] else values[0]['start']
    end = values[-1]['time'] if 'time' in values[-1] else values[-1]['end']
    return round((end-start).total_seconds() * 1000, 2)


def get_checkpoint_blocks(values: List[Dict]) -> List:
    """


    Returns:
        Dict: _description_
    """
    result = []
    for value in values:
        if 'start' in value:
            result.append({
                'description': value['description'],
                'time': f"{round((value['end']-value['start']).total_seconds() * 1000, 2)}"
            })
    return result


def get_performance_report() -> None:
    """Imprime en consola los checkpoints
    """
    if config['data']:
        result = {}
        values = list(config['data'].values())
        result['Tiempo total']=f"{get_total_time(values)}ms"
        result['Bloques']=get_checkpoint_blocks(values)
        print(json.dumps(result, indent=4, default=str))
