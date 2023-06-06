# Python Package Parallel Process

## Introducción

Esta librería contiene funciones para el manejo de tareas en procesamiento paralelo con multiprocessing asincrónico



## Desarrollo

Crear archivo `requirements.txt`:

```bash
pipenv requirements > requirements.txt
```

Si en el archivo `requirements.txt` hay una dependencia que viene de Github, deberá estar definida de la siguiente manera:
```txt
<name> @ git+https://github.com/<user>/<repo_name>.git@<id>#egg=<package>
```



Tests:

```bash
python -m unittest discover -s 'tests' -p 'test_parallel.py'
```



### Control de versiones:

```bash
git tag -a <tag> -m "<descripcion>" # Crear tag local
git push origin <tag> 				# Subir tag a repositorio remoto
git tag -d <tag> 					# Eliminar tag en forma local
git push --delete origin <tag>      # Subir tag a repositorio remoto
```



## Instalación

```bash
pipenv install git+https://github.com/lcastiglione/pp-parallel-process.git@<tag>#egg=pprocess
```



## Ejemplo de uso

`CustomController.py`:

```python
class CustomController(Worker):

    @classmethod
    def load_config(cls):
        pass

    @classmethod
    def execute(cls, params):
        results = []
        errors = None
        ... #Procesar parámetros enviados por el usuario
        return results,errors #Se devuleven siempre dos valores: Los resultados y los errores. Si no hay errores es None.
```

`main.py`:

```python
from pprocess import TaskProcess
from pprocess.exceptions import ResponseProcessException
from myproject.controller import CustomController

#Cargar parámetros
controller = CustomController()
task_process = TaskProcess(controller=controller,
                                num_processes=2,
                                max_num_process = 4,
                                chunk_requests = 30,
                                time_chunk_requests = 10)#En ms
#Iniciar el gestor de tareas en procesos paralelos
await task_process.start()

...
input_data= ...
try:
	result = await task_process.send(input_data)
    print(result)
except ResponseProcessException as exc:
    pass
...

...
input_data= [...]
try:
	results = await task_process.send_batch(input_data)
    print(results)
except ResponseProcessException as exc:
    pass
...
```



## Test de rendimiento

El test de rendimiento permite probar un Worker personalizado para distintos parámetros de configuración en TaskProcess y analizar qué parámetros son los más convenientes.