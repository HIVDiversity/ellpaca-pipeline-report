import os
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import utils
from attrs import asdict, define
from loguru import logger

# logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")


@define
class PipelineData:
    pre_post_df: pl.DataFrame
    functional_filter_df: pl.DataFrame
    attrition_df: pl.DataFrame


def load_pre_post_files(pre_dir: Path, post_dir: Path):
    """Parses files from the start and end points of a pipeline run.

    Given a set oif files fed into a pipeline run and a set of files that come out of a pipeline
    run, load all of their sequences and some stats about those sequences into a dataframe.

    Args:
        pre_dir (Path): The directory containing the input fasta files.
        post_dir (Path): The directory containing the output fasta files.

    Returns:
        pl.DataFrame: A dataframe matching sequences from before and after the pipeline was run.
    """
    df_data = []
    files = []

    logger.info("Loading all the pre files")
    for fasta_file in pre_dir.glob("*.fasta"):
        file_info = utils.get_file_info_from_name(fasta_file, "pre")
        files.append(file_info.name)
        df_data.extend(
            utils.read_fasta_file(fasta_file, "pre", sequencing_file=file_info)
        )
        logger.debug(f"Read pre file {file_info.name}")

    logger.info("Loading all the post files")
    for fasta_file in post_dir.glob("*.fasta"):
        file_info = utils.get_file_info_from_name(fasta_file, "post")

        if file_info.name not in files:
            files.append(file_info.name)
            logger.error("This should never happen...")

        df_data.extend(
            utils.read_fasta_file(fasta_file, "post", sequencing_file=file_info)
        )
        logger.debug(f"Read post file {file_info.name} (length: {len(df_data)})")

    logger.info("Converting all the information to a dataframe")
    df = pl.DataFrame([asdict(_) for _ in df_data])
    df = df.drop("path")

    return df


def load_functional_filter_reports(base_dir: Path):
    """Ingests all of the functional filter reports from all of the samples run through a pipeline into one dataframe.

    Args:
        base_dir (Path): The directory containing the functional filter reports.

    Returns:
        pl.DataFrame: A DataFrame with all of the reports concatenated rowwise.
    """
    reports: list[pl.DataFrame] = []
    logger.info("Loading reports")
    for report in base_dir.glob("*.functional_report.csv"):
        logger.debug(f"Attempting to load report {report}")
        sample_id = report.stem.split(".")[0]
        reports.append(
            pl.read_csv(
                report,
                schema={
                    "seq_name": pl.String,
                    "num_stop_codons": pl.Int64,
                    "nt_length_ungapped": pl.Int64,
                    "nt_length_gapped": pl.Int64,
                    "divisible_by_3": pl.Boolean,
                    "earliest_stop_codon": pl.Int64,
                    "earliest_stop_pct": pl.Float64,
                    "loss_from_median": pl.Float64,
                    "longest_gap_length": pl.Float64,
                    "longest_gap_location": pl.Float64,
                    "passes_frameshift_filter": pl.Boolean,
                    "passes_minimum_length_filter": pl.Boolean,
                    "passes_no_stop_codon_filter": pl.Boolean,
                    "passes_early_stop_codon_filter": pl.Boolean,
                    "flag": pl.String,
                    "passes_filter": pl.Boolean,
                },
            ).with_columns(pl.lit(sample_id).alias("sample_id"))
        )
        logger.debug(f"Loaded report for {sample_id} successfully")

    logger.info("Concatenating all the reports.")
    reports_all = pl.concat(reports)

    # Convert the contents of the sample ID field into CAPID, Visit ID, and pool.
    # This is ELLPACA-specific but could be parameterised.
    logger.info("Adding sample metadata from sample name")
    reports_all = (
        reports_all.with_columns(
            pl.col("sample_id")
            .str.split_exact("-", n=1)
            .struct.rename_fields(["id_visit", "pool"])
            .alias("fields")
        )
        .unnest("fields")
        .with_columns(
            pl.col("id_visit")
            .str.split_exact("_", n=1)
            .struct.rename_fields(["cap_id", "visit_id"])
        )
        .unnest("id_visit")
    )

    return reports_all


def generate_report_data(
    input_files: Path,
    output_files: Path,
    functional_filter_files: Path,
    pre_post_output: Path,
    functional_filter_output: Path,
    attrition_output: Path,
) -> PipelineData:
    """Generates the raw files required by the report template.


    Args:
        input_files (Path): The directory containing the raw sequences fed into the pipeline.
        output_files (Path): The directory containing the final sequences at the end of the pipeline.
        functional_filter_files (Path): The directory containing the functional filter reports.
        pre_post_output (Path): The path to write the pre-post CSV data
        functional_filter_output (Path): The path to write the report output CSV data.
        attrition_output (Path): The path to write the attrition CSV data to.
    """
    logger.info("Reading Data")
    functional_filter_df = load_functional_filter_reports(functional_filter_files)
    pre_post_df = load_pre_post_files(pre_dir=input_files, post_dir=output_files)

    logger.info("Calculating lost data between pre and post")

    lost_expr = (((pl.col("pre") - pl.col("post")) / pl.col("pre")) * 100).round(2)
    kept_expr = ((pl.col("post") / pl.col("pre")) * 100).round(2)
    attrition_df: pl.DataFrame = (
        pre_post_df.group_by(["pipeline_point", "filename"])
        .len()
        .pivot(on=["pipeline_point"], index="filename")
        .fill_null(0)
        .with_columns(
            pct_lost=lost_expr,
            num_lost=pl.col("pre") - pl.col("post"),
            pct_kept=kept_expr,
        )
    )

    attrition_df = attrition_df.sort(by="post")

    logger.info(f"Writing pre-post sequence data to {pre_post_output}")
    pre_post_df.write_csv(pre_post_output)

    logger.info(f"Writing pre-post sequence data to {functional_filter_output}")
    functional_filter_df.write_csv(functional_filter_output)

    logger.info(f"Writing attrition data to {attrition_output}")
    attrition_df.write_csv(attrition_output)

    logger.info("Done.")
    return PipelineData(
        pre_post_df=pre_post_df,
        functional_filter_df=functional_filter_df,
        attrition_df=attrition_df,
    )


def print_msa_grid(
    msa_dir: Path, width: Optional[int] = 4, height: Optional[int] = None
):
    files = []

    for file in msa_dir.glob("*"):
        if os.stat(file).st_size > 0:
            files.append(file)

    if not width:
        cols = 4
    else:
        cols = width

    rows = int(np.ceil(len(files) / cols))

    fig, ax = plt.subplots(ncols=cols, nrows=rows)

    counter = 0
    for col in range(cols):
        for row in range(rows):
            if counter > len(files) - 1:
                break
            _, current_msa = utils.msa_to_numpy(files[counter])

            ax[row][col].imshow(current_msa, interpolation="none", cmap="viridis")
            ax[row][col].set_aspect("auto")
            ax[row][col].set_axis_off()
            ax[row][col].set_title(files[counter].stem[:6])
            counter += 1

    return fig, ax
