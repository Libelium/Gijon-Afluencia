from pydantic import BaseModel

class TableSchema(BaseModel):
    """
    It represents a table in the database.
    """

    db_schema: str
    name: str

    def __hash__(self):
        return hash((self.db_schema, self.name))
