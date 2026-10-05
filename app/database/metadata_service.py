from database.metadata import (
    COLUMN_METADATA,
    METRIC_METADATA
)


class MetadataService:

    def get_column_metadata(self):
        return COLUMN_METADATA

    def get_metric_metadata(self):
        return METRIC_METADATA

    def build_metadata_text(self):

        text = ""

        text += "COLUMN DEFINITIONS\n"
        text += "=" * 40 + "\n"

        for table, columns in COLUMN_METADATA.items():

            text += f"\nTABLE {table}\n"

            for column, metadata in columns.items():

                text += (
                    f"- {column}: "
                    f"{metadata['description']}\n"
                )

        text += "\nBUSINESS METRICS\n"
        text += "=" * 40 + "\n"

        for metric, metadata in METRIC_METADATA.items():

            text += f"\n{metric}\n"

            text += (
                f"- Description: "
                f"{metadata['description']}\n"
            )

            text += (
                f"- Formula: "
                f"{metadata['formula']}\n"
            )

            text += (
                f"- Tables: "
                f"{', '.join(metadata['tables'])}\n"
            )

        return text