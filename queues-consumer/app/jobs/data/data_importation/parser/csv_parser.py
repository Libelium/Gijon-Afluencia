import pandas as pd
from config.logging import appLogging as logging
from schemas.data_importation_request import DataImportationRequest
from jobs.data.data_importation.parser.dataframe_parser import DataFrameParser
from jobs.data.data_importation.parser.parser import DataParser


class CsvParser(DataFrameParser):
    """
    Parser specialized in reading CSV files and delegating the DataFrame
    transformation to DataFrameParser.

    Responsibilities:
    - Load CSV content into a pandas DataFrame
    - Apply minimal preprocessing when loading
    - Forward the DataFrame to DataFrameParser for unified parsing

    This class only supports CSV file extensions.
    """


    def parse(self, file_content, request: DataImportationRequest):
        """
        Read a CSV file and parse it into entity notifications.

        Args:
            file_content: Path to the CSV file to be loaded
            request: Metadata request that may provide entity information
        
        Returns:
            List of EntityDataNotification parsed from the CSV content
        
        Raises:
            Exception: If the CSV cannot be loaded or parsed successfully
        """
        try:
            if isinstance(file_content, pd.DataFrame):
                df = file_content
            else:
                df = pd.read_csv(
                    file_content,
                    skipinitialspace=True,
                    encoding="utf-8",
                    dtype=str,
                    keep_default_na=False,
                )

            return super().parse(df, request)

        except Exception as e:
            logging.error(f"Failed to load/parse CSV {file_content}: {e}", exc_info=True)
            raise
        
    def get_file_extension(self):
        """
        Return the supported file extension for parser registration.
        """
        return "csv"
