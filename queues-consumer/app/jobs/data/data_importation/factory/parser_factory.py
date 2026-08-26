from jobs.data.data_importation.parser.csv_parser import CsvParser
from jobs.data.data_importation.parser.geojson_parser import GeoJsonParser
from jobs.data.data_importation.parser.xlsx_parser import XlsxParser
from jobs.data.data_importation.parser.kml_parser import KmlParser
from jobs.data.data_importation.parser.jsonld_parser import JsonLdParser
from jobs.data.data_importation.parser.parser import DataParser
from schemas.data_importation_request import DataImportationRequest, DataImportationType


class ParserFactory:
    """
    Factory class for creating parser and file reader pairs.
    Follows the factory pattern used in the data exportation system.
    Each format type has a corresponding parser and file reader.
    """

    def __init__(self):
        """
        Initialize the factory with available parser and reader mappings.
        """
        self._parsers = {
            DataImportationType.CSV.value: CsvParser,
            DataImportationType.GEOJSON.value: GeoJsonParser,
            DataImportationType.XLSX.value: XlsxParser,
            DataImportationType.KML.value: KmlParser,
            DataImportationType.JSONLD.value: JsonLdParser,
        }

    def get_parser(self, format_type: str) -> DataParser:
        """
        Get the parser instance for the specified format type.

        Args:
            format_type: The format type (e.g., 'csv', 'xlsx', 'json')

        Returns:
            Parser instance

        Raises:
            ValueError: If the format type is not supported
        """
        builder = self._parsers.get(format_type)

        if builder is None:
            raise ValueError(
                f"Unsupported format type: {format_type}, supported types: {self._parsers.keys()}"
            )

        return builder()
