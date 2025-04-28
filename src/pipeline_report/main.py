import logging
from pathlib import Path
from generate_report_data import process_directory, read_fasta_file
from utils import get_file_info_from_name
import typer
from rich.logging import RichHandler
import polars as pl
from rich import print, print_json
from attrs import asdict

FORMAT = "%(message)s"
logging.basicConfig(
    level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
app = typer.Typer()


@app.command("load")
def load_dataset(pre_dir: Path, post_dir: Path, run_name: str):
    df_data = []
    for fasta_file in pre_dir.glob("*.fasta"):
        file_info = get_file_info_from_name(fasta_file, "pre")
        df_data.extend(read_fasta_file(fasta_file, "pre", sequencing_file=file_info))

    for fasta_file in post_dir.glob("*.fasta"):
        file_info = get_file_info_from_name(fasta_file, "post")
        df_data.extend(read_fasta_file(fasta_file, "post", sequencing_file=file_info))

    df = pl.DataFrame([asdict(_) for _ in df_data])
    df = df.drop("path")
    print(df)

    df.write_parquet(f"{run_name}_temp.parquet")


@app.command("main")
def main():
    df: pl.DataFrame = pl.read_parquet("ftc_temp.parquet")

    lost_expr = (
        (pl.col("pre") - pl.col("post")) / (pl.col("post") + pl.col("pre"))
    ) * 100
    lost_df: pl.DataFrame = (
        df.group_by(["pipeline_point", "filename"])
        .count()
        .pivot(on="pipeline_point", index="filename")
        .fill_null(0)
        .with_columns(pct_lost=lost_expr)
    )
    print(lost_df)

    pass


if __name__ == "__main__":
    app()
