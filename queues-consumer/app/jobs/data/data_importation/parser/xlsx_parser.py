import pandas as pd
from config.logging import appLogging as logging
from schemas.data_importation_request import DataImportationRequest
from jobs.data.data_importation.parser.dataframe_parser import DataFrameParser


class XlsxParser(DataFrameParser):
    """
    Parser for Excel XLSX files, leveraging the DataFrameParser to convert
    structured data into EntityDataNotification grouped by entity.
    """

    def parse(self, file_content, request: DataImportationRequest):
        """
        Read an XLSX file and parse it into entity notifications.

        Args:
            file_content: path to the XLSX file to be loaded
            request: provides metadata values for entity

        Returns:
            List of EntityDataNotification parsed from the XLSX content
        """
        try:
            if isinstance(file_content, pd.DataFrame):
                df = file_content
            else:
                df = pd.read_excel(
                    file_content,
                    dtype=str,
                    keep_default_na=False,
                    engine="openpyxl",  
                )

            return super().parse(df, request)

        except Exception as e:
            logging.error(f"Failed to load/parse XLSX {file_content}: {e}", exc_info=True)
            raise

    def get_file_extension(self):
        """
        Return the supported file extension for parser registration.
        """
        return "xlsx"
