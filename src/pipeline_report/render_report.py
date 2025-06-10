import json
import os
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import create_plots as plotter
import matplotlib.pyplot as plt
import parse_data
import plotnine as pn
import polars as pl
from jinja2 import Environment, FileSystemLoader
from loguru import logger

logger.add(
    sys.stderr, format="{time} {level} {message}", filter="prep_data", level="INFO"
)

TYPST_EXECUTABLE = Path("/home/dlejeune/.cargo/bin/typst")


def prep_data():
    template = Path(
        "/home/dlejeune/masters/pipeline_report/src/pipeline_report/templates/template.typ"
    )
    filetype = "png"
    run_name = "test_report_001"
    run_date = datetime(2025, 6, 10)
    output_dir = Path(f"/home/dlejeune/masters/pipeline_report/temp/{run_name}")
    output_dir.mkdir(exist_ok=True, parents=True)

    pre_dir = "/home/dlejeune/Documents/real_data/ellpaca_nu_merged"
    post_dir = "/home/dlejeune/results/ellpaca_nu_merged_001/reverse_translate"
    report_dir = "/home/dlejeune/results/ellpaca_nu_merged_001/functional_filter"

    git_commit_id = "abcdef"
    nextflow_params = {"a": "something"}

    logger.info("Reading in data")
    pre = Path(pre_dir)
    post = Path(post_dir)

    report_data_dir = output_dir / "data"
    report_data_dir.mkdir(exist_ok=True)

    pre_post_output = report_data_dir / f"{run_name}_pre_post.csv"
    functional_filter_output = report_data_dir / f"{run_name}_functional_filter.csv"
    attrition_output = report_data_dir / f"{run_name}_attrition.csv"

    pipeline_data = parse_data.generate_report_data(
        pre,
        post,
        Path(report_dir),
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
    msa_gridplot_fp = report_data_dir / f"{run_name}_msaGridPlot.{filetype}"
    upsetplot_fp = report_data_dir / f"{run_name}_UpSetPlot.{filetype}"
    seq_length_boxplot_fp = (
        report_data_dir / f"{run_name}_sequenceLengthBoxplot.{filetype}"
    )
    seq_count_bubbleplot_fp = (
        report_data_dir / f"{run_name}_seqCountBubblePlot.{filetype}"
    )

    seq_count_barplot_fp = report_data_dir / f"{run_name}_seqCountBarPlot.{filetype}"

    if not msa_gridplot_fp.exists():
        plotter.create_msa_gridplot(post, msa_gridplot_fp)

    if not upsetplot_fp.exists():
        plotter.create_filter_upset_plot(func_filter_df, upsetplot_fp)
    if not seq_length_boxplot_fp.exists():
        plotter.create_seq_length_boxplot(func_filter_df, seq_length_boxplot_fp)
    if not seq_count_bubbleplot_fp.exists():
        plotter.create_seq_count_bubbleplot(attrition_df, seq_count_bubbleplot_fp)

    if not seq_count_barplot_fp.exists():
        plotter.create_seq_count_barplot(attrition_df, seq_count_barplot_fp)

    logger.info("Done with plots.")
    report_json_path = report_data_dir / "data.json"
    output_df = {
        "run_name": run_name,
        "run_date": run_date.strftime("%Y-%m-%d"),
        "file_count_pre": file_count_pre,
        "file_count_post": file_count_post,
        "seq_count_pre": seq_count_pre,
        "seq_count_post": seq_count_post,
        "seq_count_lost": num_lost_seqs,
        "pct_seqs_lost": round(pct_lost_seqs, 2),
        "git_commit_hash": git_commit_id,
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
            output_df[key] = str(value.relative_to(output_dir))

    logger.info(f"Writing JSON data to {report_json_path}")
    json.dump(output_df, report_json_path.open("w"), indent=4)

    template_output_path = output_dir / f"{run_name}_report.typ"
    logger.info(f"Copying template at {template} to {template_output_path}")
    # template_output_path.write_bytes(template.read_bytes())
    logger.info("Done")
    temp_output = output_dir / "template.typ"
    compile_command = f"typst compile {temp_output}"
    logger.info(f"Running {compile_command}")
    subprocess.run(shlex.split(compile_command), shell=False)


def hydrate_template(data: dict, template: Path):
    # Set up the environment (assuming your template is in the "templates" folder)
    env = Environment(loader=FileSystemLoader(template))
    template = env.get_template("template.html")

    data["report_date"] = datetime.now().strftime("%Y-%m-%d")

    # Render the template with data
    output = template.render(**data)

    return output


def render(data: dict, output: Path, template: Path):
    hydrated_template = hydrate_template(data, template)

    with output.open(mode="w", encoding="utf") as output_fh:
        output_fh.write(hydrated_template)


if __name__ == "__main__":
    prep_data()
