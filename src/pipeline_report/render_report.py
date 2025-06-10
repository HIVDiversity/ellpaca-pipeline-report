import json
import shlex
import subprocess
import sys
from datetime import datetime
from importlib import resources
from pathlib import Path
from typing import Literal

import create_plots as plotter
import parse_data
import polars as pl
import templates
from loguru import logger

logger.add(
    sys.stderr, format="{time} {level} {message}", filter="prep_data", level="INFO"
)


def create_report_json(
    pre_dir: Path,
    post_dir: Path,
    functional_filter_dir: Path,
    report_output_dir: Path,
    run_name: str,
    run_date: datetime,
    pipeline_version: str,
    pipeline_commit_hash: str,
    graphic_filetype: Literal["png", "svg"],
    pipeline_params_fp: Path,
):
    report_output_dir.mkdir(exist_ok=True, parents=True)
    report_data_dir = report_output_dir / "data"
    report_json_path = report_data_dir / "data.json"
    report_data_dir.mkdir(exist_ok=True)

    logger.info("Reading in data")
    pre_post_output = report_data_dir / f"{run_name}_pre_post.csv"
    functional_filter_output = report_data_dir / f"{run_name}_functional_filter.csv"
    attrition_output = report_data_dir / f"{run_name}_attrition.csv"

    pipeline_data = parse_data.generate_report_data(
        pre_dir,
        post_dir,
        functional_filter_dir,
        pre_post_output=pre_post_output,
        functional_filter_output=functional_filter_output,
        attrition_output=attrition_output,
    )

    pre_post_df = pipeline_data.pre_post_df
    func_filter_df = pipeline_data.functional_filter_df
    attrition_df = pipeline_data.attrition_df

    logger.info("Calculating inline variables")

    file_count_pre = len(
        pre_post_df.filter(pl.col("pipeline_point") == "pre")["filename"].unique()
    )

    file_count_post = len(
        pre_post_df.filter(pl.col("pipeline_point") == "post")["filename"].unique()
    )

    seq_count_pre = len(pre_post_df.filter(pl.col("pipeline_point") == "pre"))
    seq_count_post = len(pre_post_df.filter(pl.col("pipeline_point") == "post"))

    num_lost_seqs = seq_count_pre - seq_count_post
    pct_lost_seqs = (num_lost_seqs / seq_count_pre) * 100

    logger.info("Producing plots.")
    msa_gridplot_fp = report_data_dir / f"{run_name}_msaGridPlot.{graphic_filetype}"
    upsetplot_fp = report_data_dir / f"{run_name}_UpSetPlot.{graphic_filetype}"
    seq_length_boxplot_fp = (
        report_data_dir / f"{run_name}_sequenceLengthBoxplot.{graphic_filetype}"
    )
    seq_count_bubbleplot_fp = (
        report_data_dir / f"{run_name}_seqCountBubblePlot.{graphic_filetype}"
    )

    seq_count_barplot_fp = (
        report_data_dir / f"{run_name}_seqCountBarPlot.{graphic_filetype}"
    )

    if not msa_gridplot_fp.exists():
        plotter.create_msa_gridplot(post_dir, msa_gridplot_fp)

    if not upsetplot_fp.exists():
        plotter.create_filter_upset_plot(func_filter_df, upsetplot_fp)
    if not seq_length_boxplot_fp.exists():
        plotter.create_seq_length_boxplot(func_filter_df, seq_length_boxplot_fp)
    if not seq_count_bubbleplot_fp.exists():
        plotter.create_seq_count_bubbleplot(attrition_df, seq_count_bubbleplot_fp)

    if not seq_count_barplot_fp.exists():
        plotter.create_seq_count_barplot(attrition_df, seq_count_barplot_fp)

    logger.info("Done with plots.")
    logger.info("Reading pipeline parameters")

    if pipeline_params_fp.exists():
        nextflow_params = json.load(pipeline_params_fp.open("r"))
    else:
        nextflow_params = {}

    output_df = {
        "run_name": run_name,
        "run_date": run_date.strftime("%Y-%m-%d"),
        "file_count_pre": file_count_pre,
        "file_count_post": file_count_post,
        "seq_count_pre": seq_count_pre,
        "seq_count_post": seq_count_post,
        "seq_count_lost": num_lost_seqs,
        "pct_seqs_lost": round(pct_lost_seqs, 2),
        "git_commit_hash": pipeline_commit_hash,
        "nf_param_dump": nextflow_params,
        "img_msa_gridplot": msa_gridplot_fp,
        "img_upsetplot": upsetplot_fp,
        "img_seq_length_boxplot": seq_length_boxplot_fp,
        "img_seq_count_bubbleplot": seq_count_bubbleplot_fp,
        "img_seq_count_barplot": seq_count_barplot_fp,
    }

    ## Transform paths into strings relative to output directory
    for key, value in output_df.items():
        if isinstance(value, Path):
            output_df[key] = str(value.relative_to(report_output_dir))

    logger.info(f"Writing JSON data to {report_json_path}")
    json.dump(output_df, report_json_path.open("w"), indent=4)


def render(
    pre_dir: Path,
    post_dir: Path,
    functional_filter_dir: Path,
    report_output_dir: Path,
    run_name: str,
    run_date: datetime,
    pipeline_version: str,
    pipeline_commit_hash: str,
    graphic_filetype: Literal["png", "svg"],
    nextflow_params_fp: Path,
):
    create_report_json(
        pre_dir,
        post_dir,
        functional_filter_dir,
        report_output_dir,
        run_name,
        run_date,
        pipeline_version,
        pipeline_commit_hash,
        graphic_filetype,
        nextflow_params_fp,
    )

    template_file = resources.files(templates) / "template.typ"
    template_output_path = report_output_dir / f"{run_name}_report.typ"
    logger.info(f"Copying template at {template_file} to {template_output_path}")
    template_output_path.write_bytes(template_file.read_bytes())
    logger.info("Done")

    compile_command = f"typst compile {template_output_path}"
    logger.info(f"Running {compile_command}")
    subprocess.run(shlex.split(compile_command), shell=False)


def test_render():
    run_name = "test_report_001"
    run_date = datetime(2025, 6, 10)
    output_dir = Path(f"/home/dlejeune/masters/pipeline_report/temp/{run_name}")

    pre_dir = "/home/dlejeune/Documents/real_data/ellpaca_nu_merged"
    post_dir = "/home/dlejeune/results/ellpaca_nu_merged_001/reverse_translate"
    report_dir = "/home/dlejeune/results/ellpaca_nu_merged_001/functional_filter"

    render(
        Path(pre_dir),
        Path(post_dir),
        Path(report_dir),
        output_dir,
        run_name,
        run_date,
        "1.0.0",
        "abcdefg",
        "png",
        Path("/doesntexist"),
    )


if __name__ == "__main__":
    test_render()
