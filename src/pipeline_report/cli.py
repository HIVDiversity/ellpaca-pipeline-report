from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from loguru import logger

from pipeline_report import render_report

app = typer.Typer()


@app.command("render")
def render_report_cli(
    pipeline_pre_dir: Annotated[
        Path,
        typer.Argument(
            help="Directory containing files that were handed to the pipeline.",
            file_okay=False,
        ),
    ],
    pipeline_post_dir: Annotated[
        Path,
        typer.Argument(
            help="Directory containing files at the last point of the pipeline.",
            file_okay=False,
        ),
    ],
    pipeline_functional_filter_dir: Annotated[
        Path,
        typer.Argument(
            help="Directory containing the functional filter reports.",
            file_okay=False,
        ),
    ],
    output_dir: Annotated[
        Path,
        typer.Argument(
            help="Location where output is going to be written.",
            file_okay=False,
        ),
    ],
    run_name: Annotated[
        str, typer.Argument(help="Name of the run which will be used in the report.")
    ],
    pipeline_version: Annotated[
        str, typer.Option(help="Version of the pipeline")
    ] = None,
    pipeline_commit_hash: Annotated[
        str, typer.Option(help="Git commit hash that the pipeline was run with")
    ] = None,
    run_date: Annotated[
        datetime, typer.Option(help="Datetime when the pipeline was run.")
    ] = datetime.today(),
    nextflow_params_fp: Annotated[
        Path, typer.Option(help="Path to the nextflow params as a JSON file.")
    ] = None,
):
    logger.info("Creating JSON data.")
    render_report.create_report_json(
        pipeline_pre_dir,
        pipeline_post_dir,
        pipeline_functional_filter_dir,
        output_dir,
        run_name,
        run_date,
        pipeline_version,
        pipeline_commit_hash,
        "png",
        nextflow_params_fp,
    )

    logger.info("Rendering report")
    render_report.render(output_dir, run_name)
    pass


def cli_entrypoint():
    app()


if __name__ == "__main__":
    cli_entrypoint()
