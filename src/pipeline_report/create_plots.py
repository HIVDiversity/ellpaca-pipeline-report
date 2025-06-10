import os
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import plotnine as pn
import polars as pl
import upsetplot
import utils
from loguru import logger

# logger.add(sys.stderr, format="{time} {level} {message}", filter="plots", level="INFO")


def create_msa_gridplot(
    data: Path, output: Path, width: Optional[int] = 4, height: Optional[int] = None
) -> None:
    """Produces a grid of zoomed out MSA grids.

    Useful for showing a high-level overview of the MSAs produced.

    Args:
        data (Path): A path to a directory containing the FASTA files to draw
        output (Path): The path to write the output to
        width (Optional[int]): Number of columns to have in the grid. Defaults to 4
        height (Optional[int]): Unset. Don't use
    """
    # Create the MSA Grid. Move to new function

    logger.info("Producing MSA grid plot")

    files = []

    for file in data.glob("*"):
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

    fig.set_size_inches(13, 25)
    fig.tight_layout()

    logger.info(f"Writing to {output}")
    fig.savefig(output)


def create_filter_upset_plot(data: pl.DataFrame, output: Path) -> None:
    """Produces an UpSet plot from the filtering data.

    Args:
        data (pl.DataFrame): A polars DataFrame with the functional filter data
        output (Path): Path to write the output to
    """

    logger.info("Producing UpSet plot")

    upsetdata = upsetplot.from_indicators(
        data.select(
            [
                pl.col("passes_frameshift_filter"),
                pl.col("passes_minimum_length_filter"),
                pl.col("passes_no_stop_codon_filter"),
                pl.col("passes_early_stop_codon_filter"),
            ]
        ).to_pandas()
    )
    fig = plt.figure()
    upsetplot.UpSet(
        upsetdata,
        subset_size="count",
        show_counts=True,
        sort_by="cardinality",
        element_size=50,
    ).plot(fig)

    logger.info(f"Writing to {output}")
    fig.savefig(output, dpi=1200)
    fig.savefig(output.with_suffix(".svg"), dpi=1200)


def create_seq_length_boxplot(data: pl.DataFrame, output: Path) -> None:
    """Produces a boxplot of sequence length for each file

    Args:
        data (pl.DataFrame): A dataframe containing the results from the functional filter
        output (Path): The path to write the output to
    """
    logger.info("Producing sequence length boxplot")
    length_boxplot = (
        pn.ggplot(
            data.sort(by="sample_id").filter(pl.col("passes_filter")),
            pn.aes(y="nt_length_ungapped", x="sample_id", color="sample_id"),
        )
        + pn.geom_boxplot()
        + pn.labs(y="Sequence Nucleotide Length (without gaps)", x="Sample")
        + pn.coord_flip()
        + pn.theme_classic()
        + pn.theme(legend_position="none")
    )

    logger.info(f"Writing to {output}")
    pn.ggsave(length_boxplot, filename=output, width=8.27, height=11.69, dpi=1200)
    pn.ggsave(
        length_boxplot,
        filename=output.with_suffix(".svg"),
        width=8.27,
        height=11.69,
        dpi=1200,
    )


def create_seq_count_bubbleplot(data: pl.DataFrame, output: Path) -> None:
    """Produces a bubbleplot showing sequence count before and after being run through the pipeline

    Args:
        data (pl.DataFrame): A dataframe with sequence attrition data
        output (Path): The path to save the plot to.
    """
    logger.info("Producing sequence count bubbleplot")
    seq_attrition_bubble_plot = (
        pn.ggplot(
            data.with_columns(
                label=pl.when(pl.col("pct_lost") >= 60)
                .then(pl.col("filename"))
                .otherwise(pl.lit("")),
            ),
            pn.aes(x="pre", y="post", size="pct_lost", fill="pct_lost"),
        )
        + pn.geom_point()
        + pn.geom_label(pn.aes(label="label"), nudge_y=0.2)
        + pn.scale_x_log10()
        + pn.scale_y_log10()
        + pn.labs(
            x="Sequence Count Pre-Pipeline",
            y="Sequence Count Post-Pipeline",
            fill="Percent Lost",
        )
        + pn.scale_size(guide=None)
        + pn.theme_bw()
        + pn.theme(legend_position="top")
    )
    logger.info(f"Writing to {output}")
    pn.ggsave(seq_attrition_bubble_plot, filename=output, width=8, height=6, dpi=1200)
    pn.ggsave(
        seq_attrition_bubble_plot,
        filename=output.with_suffix(".svg"),
        width=8,
        height=6,
        dpi=1200,
    )


def create_seq_count_barplot(data: pl.DataFrame, output: Path) -> None:
    """Produces a barplot of sequence count post-pipeline run for each sample.

    Args:
        data (pl.DataFrame): Dataframe with attrition data.
        output (Path): Path to save the plot to.
    """
    logger.info("Creating sequence count bar plot.")
    file_size_plot = (
        pn.ggplot(
            data,
            pn.aes(x="filename", y="post", fill="pct_lost"),
        )
        + pn.geom_col()
        + pn.scale_y_log10()
        + pn.labs(
            y="Sequence Count",
            x="Sample",
            fill="Percent Lost",
        )
        + pn.scale_x_discrete(
            limits=data.sort(by="post", descending=False)["filename"].to_list()
        )
        + pn.theme(legend_position="top")
        + pn.coord_flip()
    )

    logger.info(f"Writing plot to {output}")
    pn.ggsave(file_size_plot, filename=output, width=8.27, height=11.69, dpi=1200)
    pn.ggsave(
        file_size_plot,
        filename=output.with_suffix(".svg"),
        width=8.27,
        height=11.69,
        dpi=1200,
    )
