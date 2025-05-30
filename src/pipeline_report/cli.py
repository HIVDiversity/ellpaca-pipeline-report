from pathlib import Path
from typing import Annotated

import typer
from loguru import logger
from parse_data import generate_report_data

app = typer.Typer()


@app.command("parse-run-data")
def generate_report_data_cli(
    input_files: Annotated[
        Path,
        typer.Argument(
            help="Directory containing files that were handed to the pipeline.",
            file_okay=False,
        ),
    ],
    output_files: Annotated[
        Path,
        typer.Argument(
            help="Directory containing files at the last point of the pipeline.",
            file_okay=False,
        ),
    ],
    report_files: Annotated[
        Path,
        typer.Argument(
            help="Directory containing the functional filter reports.",
            file_okay=False,
        ),
    ],
    run_name: Annotated[
        str, typer.Argument(help="Name of the run which will be used in the report.")
    ],
    output_location: Annotated[Path, typer.Argument(help="Where to output the report")],
) -> None:
    generate_report_data(
        input_files,
        output_files,
        report_files,
        output_location / f"{run_name}_prepost.csv",
        output_location / f"{run_name}_reports.csv",
    )


if __name__ == "__main__":
    app()
