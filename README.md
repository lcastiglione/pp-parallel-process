# Python Package Parallel Process

## Introducción

Esta librería contiene funciones para el manejo de tareas en procesamiento paralelo con multiprocessing asincrónico

Su principal uso es para dividir ejecuciones que consumen procesamiento de CPU y que no bloqueen el hilo principal. Se reciben parámetros por parte del usuario, se lo deja en espera en forma asíncrona para no bloquear el hilo principal y cuando se termina de ejecutar los cálculo se devuelve el resultado.

Ejemplo de usos:

- Servidor que recibe peticiones para procesar un dato. Se deja en espera dicha petición hasta que se termine el cálculo y mientras tanto se procesan las otras peticiones.
- Procesar un grupo de datos en múltiples procesos.
- Procesamiento de datos con modelos de lenguaje de inteligencia artificial.

EL funcionamiento de la librería se basa en recibir peticiones de trabajo, agrupar las peticiones simples en lotes en una ventana de tiempo y luego enviar dichos lotes a los procesos disponibles. No importa si las peticiones fueron hechas por distintos usuarios ya que cada petición tiene un ID que permite rastrear el origen de la petición y devolver el resultado correcto al usuario correspondiente.

Además, el sistema crea y destruye procesos en forma dinámica y automática, cuando el uso de la CPU sea más o menos intensivo.

Es importante tener en cuenta, que los parámetros de entrada que se van a usar para realizar cálculos tienen que ser lo más simples posibles ya que los mismos, cuando se envían al proceso, sufren un pre-procesamiento que genera un delay. Mientras más complejo es el objeto, más tiempo se tarda en el pre-procesamiento y, por ende, más tiempo se tarda en la ejecución de la petición. Evitar enviar funciones u objetos complejos.



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
git push origin <tag>               # Subir tag a repositorio remoto
git tag -d <tag>                    # Eliminar tag en forma local
git push --delete origin <tag>      # Subir tag a repositorio remoto
```



## Instalación

```bash
pipenv install git+https://github.com/lcastiglione/pp-pprocess#egg=pprocess
```



## Ejemplo de uso

`controller.py`:

```python
from pprocess import Worker

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