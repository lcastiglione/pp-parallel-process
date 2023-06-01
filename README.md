# Python Package Parallel Process

## Introducción

Esta librería contiene funciones para el manejo de tareas en procesamiento paralelo con multiprocessing asincrónico



## Desarrollo

Crear archivo `requirements.txt`:

```bash
pipenv requirements > requirements.txt
```

Tests:

```bash
python -m unittest discover -s 'tests' -p 'test_parallel.py'
```



## Instalación

```bash
pipenv install git+https://github.com/lcastiglione/pp-pprocess#egg=pprocess
```



## Ejemplo de uso

```python
```



## Test de rendimiento

El test de rendimiento permite probar un Worker personalizado para distintos parámetros de configuración en TaskProcess y analizar qué parámetros son los más convenientes.