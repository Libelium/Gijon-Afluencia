import abc

#Esta clase Base ETL define una estructura común para las clases que realizarán procesos de ETL,
# estableciendo una interfaz a través de los métodos abstractos que deben implementarse en las subclases


class BaseETL(abc.ABC):

    @abc.abstractmethod
    def init_etl(self):  # pragma: no cover
        raise NotImplementedError('you must implement this method')

    @abc.abstractmethod
    def extract(self):  # pragma: no cover
        raise NotImplementedError('you must implement this method')

    @abc.abstractmethod
    def transform(self):  # pragma: no cover
        raise NotImplementedError('you must implement this method')

    @abc.abstractmethod
    def load(self): # pragma: no cover
        raise NotImplementedError('you must implement this method')

# El método execute no es abstracto, y lo que hace es llamar a los métodos abstractos anteriores.
# Si estos métodos se ejecutan con éxito(retornan TRUE), sale con un código de salida 0 (ejecución exitosa). En caso
# contrario, sale con código de salida 1.


    def execute(self):
        if self.init_etl() and self.extract() and self.transform() and self.load():
            exit(0)

        exit(1)

    def execute_once(self):
        if self.init_etl() and self.extract() and self.transform() and self.load():
            return 0

        return -1
