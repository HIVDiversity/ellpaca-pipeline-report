import json
import os
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import parse_data
import plotnine as pn
import polars as pl
import upsetplot
from jinja2 import Environment, FileSystemLoader
from loguru import logger


def prep_data():
    logger.add(
        sys.stderr, format="{time} {level} {message}", filter="prep_data", level="INFO"
    )
    template = Path(
        "/home/dlejeune/masters/pipeline_report/src/pipeline_report/templates/template.typ"
    )
    run_name = "test_report_001"
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

    report_df = parse_data.load_functional_filter_reports(Path(report_dir))

    pre_post_df = parse_data.load_pre_post_files(pre, post)
    lost_expr = (((pl.col("pre") - pl.col("post")) / pl.col("pre")) * 100).round(2)
    kept_expr = ((pl.col("post") / pl.col("pre")) * 100).round(2)

    lost_df = (
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

    logger.info("Calculating inline variables")
    # Produce inline variables

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
    logger.info("Producing MSA grid plot.")
    # Create the MSA Grid. Move to new function
    fig, ax = parse_data.print_msa_grid(post)
    fig.set_size_inches(13, 25)
    fig.tight_layout()
    msa_qualityplot_filename = report_data_dir / "msa_qualityplot.svg"
    logger.info(f"Writing to {msa_qualityplot_filename}")
    fig.savefig(msa_qualityplot_filename)
    ## end

    logger.info("Producing UpSet plot")
    # Create UpSet plot
    upsetdata = upsetplot.from_indicators(
        report_df.select(
            [
                pl.col("passes_frameshift_filter"),
                pl.col("passes_minimum_length_filter"),
                pl.col("passes_no_stop_codon_filter"),
                pl.col("passes_early_stop_codon_filter"),
            ]
        ).to_pandas()
    )
    fig = plt.figure()
    axs = upsetplot.UpSet(
        upsetdata,
        subset_size="count",
        show_counts=True,
        sort_by="cardinality",
        element_size=50,
    ).plot(fig)

    upsetplot_filepath = report_data_dir / "loss_upset.svg"
    logger.info(f"Writing to {upsetplot_filepath}")
    fig.savefig(upsetplot_filepath)
    ## end
    logger.info("Producing length boxplot")
    # Create length barplot
    length_boxplot = (
        pn.ggplot(
            report_df.sort(by="sample_id").filter(pl.col("passes_filter")),
            pn.aes(y="nt_length_ungapped", x="sample_id", color="sample_id"),
        )
        + pn.geom_boxplot()
        + pn.labs(y="Sequence Nucleotide Length (without gaps)", x="Sample")
        + pn.coord_flip()
        # + pn.theme_minimal()
        + pn.theme(legend_position="none")
    )
    length_boxplot_filename = report_data_dir / "length_boxplot.svg"
    logger.info(f"Writing to {length_boxplot_filename}")
    pn.ggsave(
        length_boxplot, filename=length_boxplot_filename, width=8.27, height=11.69
    )
    ## end

    logger.info("Creating sequence loss barplot")
    # create sequence loss barplot
    seq_loss_barplot = (
        pn.ggplot(
            lost_df.unpivot(
                index=["filename"],
                on=["pct_lost", "pct_kept"],
                value_name="pct_lost",
                variable_name="pipeline_point",
            )
            .with_columns(
                pipeline_point=pl.when(pl.col("pipeline_point") == "pct_kept")
                .then(pl.lit("Retained"))
                .otherwise(pl.lit("Rejected"))
            )
            .sort(by="filename"),
            pn.aes(x="filename", y="pct_lost", fill="pipeline_point"),
        )
        + pn.geom_col(position=pn.position_stack())
        + pn.geom_col()
        + pn.labs(x="Sample", y="Percent of total", fill="Status")
        + pn.scale_fill_ordinal()
        + pn.coord_flip()
    )
    seq_loss_barplot_filename = report_data_dir / "seq_loss_barplot.svg"
    logger.info(f"Writing to {seq_loss_barplot_filename}")
    pn.ggsave(
        seq_loss_barplot, filename=seq_loss_barplot_filename, width=8.27, height=11.69
    )

    logger.info("Producing attrition bubbleplot")
    seq_attrition_bubble_plot = (
        pn.ggplot(
            lost_df.with_columns(
                # pre=pl.col("pre").log10(),
                # post=pl.col("post").log10(),
                label=pl.when(pl.col("pct_lost") >= 60)
                .then(pl.col("filename"))
                .otherwise(pl.lit("")),
            ),
            pn.aes(x="pre", y="num_lost", size="pct_lost", fill="pct_lost"),
        )
        + pn.geom_point()
        + pn.geom_label(pn.aes(label="label"), nudge_y=0.2)
        + pn.scale_x_log10()
        + pn.scale_y_log10()
        + pn.labs(
            x="Sequence Count Pre-Pipeline",
            y="Number of Sequences Lost",
            fill="Percent Lost",
        )
    )
    seq_attrition_bubble_plot_filename = report_data_dir / "seq_loss_bubbleplot.svg"
    logger.info(f"Writing to {seq_attrition_bubble_plot_filename}")
    pn.ggsave(
        seq_attrition_bubble_plot,
        filename=seq_attrition_bubble_plot_filename,
        width=8,
        height=6,
    )
    ## end
    logger.info("Done with plots.")
    report_json_path = report_data_dir / "data.json"
    output_df = {
        "run_name": run_name,
        "file_count_pre": file_count_pre,
        "file_count_post": file_count_post,
        "seq_count_pre": seq_count_pre,
        "seq_count_post": seq_count_post,
        "seq_count_lost": num_lost_seqs,
        "pct_seqs_lost": round(pct_lost_seqs, 2),
        "git_commit_hash": git_commit_id,
        "nf_param_dump": nextflow_params,
        "img_msa_grid_path": str(msa_qualityplot_filename.relative_to(output_dir)),
        "img_upset_plot_path": str(upsetplot_filepath.relative_to(output_dir)),
        "img_length_boxplot_path": str(length_boxplot_filename.relative_to(output_dir)),
        "img_seq_loss_barplot": str(seq_loss_barplot_filename.relative_to(output_dir)),
        "img_seq_attrition_bubbleplot_path": str(
            seq_attrition_bubble_plot_filename.relative_to(output_dir)
        ),
    }
    logger.info(f"Writing JSON data to {report_json_path}")
    json.dump(output_df, report_json_path.open("w"), indent=4)

    template_output_path = output_dir / f"{run_name}_report.typ"
    logger.info(f"Copying template at {template} to {template_output_path}")
    template_output_path.write_bytes(template.read_bytes())
    logger.info("Done")


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
