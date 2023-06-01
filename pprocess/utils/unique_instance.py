'''
Módulo que contiene la definición de la clase Singleton para que la utilice EventBus
'''


class UniqueInstance(type):
    """Clase que define las propiedades según el patrón singleton
    """
    _instance: 'UniqueInstance' = None

    def __call__(cls, *args, **kwargs) -> 'UniqueInstance':
        """
        Método que crea la instancia de la clase si no existe.

        Returns:
            UniqueInstance: Instancia de la clase.

        """
        if not cls._instance:
            instance = super().__call__(*args, **kwargs)
            cls._instance = instance
        return cls._instance

    @staticmethod
    def remove_instance(instance_class: 'UniqueInstance') -> None:
        """
        Método estático que elimina la instancia de EventBus
        """
        instance_class._instance = None  # pylint: disable=W0212
