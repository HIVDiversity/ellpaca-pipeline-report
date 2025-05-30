# import logging
# from pathlib import Path
# from typing import Annotated

# import polars as pl
# import typer
# from attrs import asdict
# from generate_report_data import process_directory, read_fasta_file
# from render_report import render
# from rich import print, print_json
# from rich.logging import RichHandler
# from utils import get_file_info_from_name

# FORMAT = "%(message)s"
# logging.basicConfig(
#     level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
# )
# app = typer.Typer()


# @app.command("load")
# def load_dataset(pre_dir: Path, post_dir: Path, report_dir: Path, run_name: str):
#     df_data = []
#     files = []

#     logging.info("Loading all the pre files")
#     for fasta_file in pre_dir.glob("*.fasta"):
#         file_info = get_file_info_from_name(fasta_file, "pre")
#         files.append(file_info.name)
#         df_data.extend(read_fasta_file(fasta_file, "pre", sequencing_file=file_info))
#         logging.debug(f"Read pre file {file_info.name}")

#     logging.info("Loading all the post files")
#     for fasta_file in post_dir.glob("*.fasta"):
#         file_info = get_file_info_from_name(fasta_file, "post")

#         if file_info.name not in files:
#             files.append(file_info.name)
#             logging.error("This should never happen...")

#         df_data.extend(read_fasta_file(fasta_file, "post", sequencing_file=file_info))
#         logging.debug(f"Read post file {file_info.name} (data: {len(df_data)}")

#     logging.info("Converting all the information to a dataframe")
#     df = pl.DataFrame([asdict(_) for _ in df_data])
#     df = df.drop("path")

#     return df


# @app.command("load_reports")
# def load_functional_filter_reports(base_dir: Path):
#     reports: list[pl.DataFrame] = []
#     logging.info("Loading reports")
#     for report in base_dir.glob("*.functional_report.csv"):
#         logging.debug(f"Attempting to load report {report}")
#         sample_id = report.stem.split(".")[0]
#         reports.append(
#             pl.read_csv(
#                 report,
#                 schema={
#                     "seq_name": pl.String,
#                     "num_stop_codons": pl.Int64,
#                     "nt_length_ungapped": pl.Int64,
#                     "nt_length_gapped": pl.Int64,
#                     "divisible_by_3": pl.Boolean,
#                     "earliest_stop_codon": pl.Int64,
#                     "earliest_stop_pct": pl.Float64,
#                     "loss_from_median": pl.Float64,
#                     "longest_gap_length": pl.Float64,
#                     "longest_gap_location": pl.Float64,
#                     "passes_frameshift_filter": pl.Boolean,
#                     "passes_minimum_length_filter": pl.Boolean,
#                     "passes_no_stop_codon_filter": pl.Boolean,
#                     "passes_early_stop_codon_filter": pl.Boolean,
#                     "flag": pl.String,
#                     "passes_filter": pl.Boolean,
#                 },
#             ).with_columns(pl.lit(sample_id).alias("sample_id"))
#         )
#         logging.debug(f"Loaded report for {sample_id} successfully")

#     logging.info("Concatenating all the reports.")
#     reports_all = pl.concat(reports)
#     return reports_all


# @app.command("parse-run-data")
# def generate_report_data_cli(
#     input_files: Annotated[
#         Path,
#         typer.Argument(
#             help="Directory containing files that were handed to the pipeline.",
#             file_okay=False,
#         ),
#     ],
#     output_files: Annotated[
#         Path,
#         typer.Argument(
#             help="Directory containing files at the last point of the pipeline.",
#             file_okay=False,
#         ),
#     ],
#     report_files: Annotated[
#         Path,
#         typer.Argument(
#             help="Directory containing the functional filter reports.",
#             file_okay=False,
#         ),
#     ],
#     run_name: Annotated[
#         str, typer.Argument(help="Name of the run which will be used in the report.")
#     ],
#     output_location: Annotated[Path, typer.Argument(help="Where to output the report")],
# ):
#     logging.info("Reading Data")
#     report_df = load_functional_filter_reports(report_files)
#     pre_post_df = load_dataset(
#         pre_dir=input_files,
#         post_dir=output_files,
#         report_dir=report_files,
#         run_name=run_name,
#     )
#     logging.info("Calculating lost data between pre and post")
#     lost_expr = (((pl.col("pre") - pl.col("post")) / pl.col("pre")) * 100).round(2)

#     lost_df: pl.DataFrame = (
#         pre_post_df.group_by(["pipeline_point", "filename"])
#         .len()
#         .pivot(on="pipeline_point", index="filename")
#         .fill_null(0)
#         .with_columns(pct_lost=lost_expr, num_lost=pl.col("pre") - pl.col("post"))
#     )
#     # New pre_post_df: average before/after: count, length + max, min
#     logging.info("Calculating lost sequence summary stats")
#     summary_stat_df = (
#         pre_post_df.group_by(["pipeline_point", "filename"])
#         .agg(
#             total_seqs=pl.col("name").len(),
#             average_len=pl.col("length").mean(),
#             min_length=pl.col("length").min(),
#             max_len=pl.col("length").max(),
#         )
#         .pivot(on="pipeline_point", index="filename")
#     )

#     logging.info("Calculating abridged stats")
#     abridged_stats = summary_stat_df.describe().drop("filename")

#     logging.info("Looking at the reports and aggregating data")
#     summary_report = report_df.group_by("sample_id").agg(
#         pl.len(),
#         (pl.col("num_stop_codons") > 3).sum().alias("num_stop_codons_gt_3"),
#         (pl.col("earliest_stop_pct") < 90).sum().alias("num_earliest_stop_lt_90"),
#         pl.col("passes_filter").sum(),
#         (pl.col("divisible_by_3") == False).sum().alias("contains_frameshift"),
#     )
#     lost_df = lost_df.sort(by="post")

#     # data = {
#     #     "attrition_data": lost_df.to_dicts(),
#     #     "report_title": "",
#     #     "run_name": run_name,
#     #     "abridged_summary": abridged_stats.to_dicts(),
#     #     "summary_filter_report": summary_report.to_dicts(),
#     #     "report_table": report_df.to_dicts(),
#     # }

#     logging.info(f"Writing data in {output_location}")
#     pre_post_df.write_csv(output_location / f"{run_name}_prepost.csv")
#     report_df.write_csv(output_location / f"{run_name}_allreports.csv")


# @app.command("generate-report")
# def do_report(input_files: Path, output_files: Path, report_files: Path, run_name: str):
#     logging.info("Reading Data")
#     report_df = load_functional_filter_reports(report_files)
#     pre_post_df = load_dataset(
#         pre_dir=input_files,
#         post_dir=output_files,
#         report_dir=report_files,
#         run_name=run_name,
#     )
#     logging.info("Calculating lost data between pre and post")
#     lost_expr = (((pl.col("pre") - pl.col("post")) / pl.col("pre")) * 100).round(2)

#     lost_df: pl.DataFrame = (
#         pre_post_df.group_by(["pipeline_point", "filename"])
#         .len()
#         .pivot(on="pipeline_point", index="filename")
#         .fill_null(0)
#         .with_columns(pct_lost=lost_expr, num_lost=pl.col("pre") - pl.col("post"))
#     )
#     # New pre_post_df: average before/after: count, length + max, min
#     logging.info("Calculating lost sequence summary stats")
#     summary_stat_df = (
#         pre_post_df.group_by(["pipeline_point", "filename"])
#         .agg(
#             total_seqs=pl.col("name").len(),
#             average_len=pl.col("length").mean(),
#             min_length=pl.col("length").min(),
#             max_len=pl.col("length").max(),
#         )
#         .pivot(on="pipeline_point", index="filename")
#     )

#     logging.info("Calculating abridged stats")
#     abridged_stats = summary_stat_df.describe().drop("filename")

#     logging.info("Looking at the reports and aggregating data")
#     summary_report = report_df.group_by("sample_id").agg(
#         pl.len(),
#         (pl.col("num_stop_codons") > 3).sum().alias("num_stop_codons_gt_3"),
#         (pl.col("earliest_stop_pct") < 90).sum().alias("num_earliest_stop_lt_90"),
#         pl.col("passes_filter").sum(),
#         (pl.col("divisible_by_3") == False).sum().alias("contains_frameshift"),
#     )
#     lost_df = lost_df.sort(by="post")

#     data = {
#         "attrition_data": lost_df.to_dicts(),
#         "report_title": "",
#         "run_name": run_name,
#         "abridged_summary": abridged_stats.to_dicts(),
#         "summary_filter_report": summary_report.to_dicts(),
#         "report_table": report_df.to_dicts(),
#     }
#     #
#     logging.info("Rendering the report")
#     pre_post_df.write_csv(Path(f"{run_name}_prepost.csv"))
#     report_df.write_csv(Path(f"{run_name}_allreports.csv"))
#     render(data, Path(f"{run_name}_report.html"), Path("src/pipeline_report/templates"))


# if __name__ == "__main__":
#     app()
