from pydantic import BaseModel


class Entity(BaseModel):
    """
    It represents an entity in the context broker,
    but also should be optimized to be used in the queries to
    the Quantum Leap data source.
    """

    tenant: str
    scope: str
    urn: str

    def __hash__(self):
        return hash((self.tenant, self.scope, self.urn))
