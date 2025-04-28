from pathlib import Path
import logging
from rich.logging import RichHandler
from typing_extensions import Optional
from attrs import define, asdict


@define
class FileStats:
    num_sequences: int
    average_length: float
    max_length: int
    min_length: int
    filename: Optional[str]


@define
class SequencingFile:
    name: str
    pool: str
    visit: str
    participant: str
    path: Path
    pipeline_point: str


@define
class Sequence:
    name: str
    length: int
    pool: str
    visit: str
    participant: str
    path: Path
    pipeline_point: str
    filename: str


FORMAT = "%(message)s"
logging.basicConfig(
    level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)


def get_file_info_from_name(
    file: Path, pipeline_point: Optional[str]
) -> SequencingFile:
    file_name = file.stem
    participant_id = file_name.split("_")[0]
    visit_id = file_name[7:11]
    pool_id = file_name.split("-")[1].split(".")[0]

    return SequencingFile(
        name=file_name.split(".")[0],
        pool=pool_id,
        visit=visit_id,
        participant=participant_id,
        path=file,
        pipeline_point=pipeline_point,
    )


def read_fasta_to_dict(filepath: Path) -> dict[str, str]:
    """Reads a FASTA-formatted file into a python dictionary

    Args:
        filepath (Path): The path to the fasta file

    Returns:
        dict[str, str]: A dictionary where the sequence IDs are the keys, and the sequences are the values
    """

    fasta_string_lines = open(filepath, "r").readlines()

    sequences = {}
    header = ""
    for line in fasta_string_lines:
        line = line.strip()
        if line.startswith(">"):
            header = line.strip().strip(">")
            if header in sequences:
                logging.warning(
                    f"There is already a line with the header {header} and it will be overwritten"
                )
            sequences[header] = ""
        else:
            sequences[header] += line.strip()

    return sequences
