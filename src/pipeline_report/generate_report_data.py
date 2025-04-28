import logging
from pathlib import Path
from typing import Optional

from attrs import asdict
from rich.logging import RichHandler
from utils import read_fasta_to_dict, FileStats, Sequence, SequencingFile
from Bio import SeqIO

FORMAT = "%(message)s"
logging.basicConfig(
    level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)


def read_fasta_file(
    file: Path,
    sequencing_timepoint: str,
    sequencing_file: Optional[SequencingFile] = None,
    name: Optional[str] = None,
    participant: Optional[str] = None,
    visit: Optional[str] = None,
    pool: Optional[str] = None,
) -> list[Sequence]:
    reader = SeqIO.parse(file, "fasta")

    if not sequencing_file:
        sequencing_file: SequencingFile = SequencingFile(
            name=name,
            pool=pool,
            visit=visit,
            participant=participant,
            path=file,
            pipeline_point=sequencing_timepoint,
        )

    seqs = []
    for sequence in reader:
        seq_stats = Sequence(
            name=sequence.id,
            length=len(sequence.seq),
            pool=sequencing_file.pool,
            visit=sequencing_file.visit,
            participant=sequencing_file.participant,
            path=sequencing_file.path,
            pipeline_point=sequencing_file.pipeline_point,
            filename=sequencing_file.name,
        )
        seqs.append(seq_stats)

    return seqs


def get_stats_for_file(file: Path) -> FileStats:
    """Gets basic sequence statistics from a file.

    Args:
        file (Path): The file to process

    Returns:
        FileStats: The stats about the sequences in that file
    """
    fasta_dict = read_fasta_to_dict(file)

    lengths: list[int] = []

    for seq_id, seq in fasta_dict.items():
        lengths.append(len(seq))

    if lengths:
        max_length = max(lengths)
        min_length = min(lengths)
        avg_length = sum(lengths) / len(lengths)
    else:
        max_length = 0
        min_length = 0
        avg_length = 0

    stats = FileStats(
        len(fasta_dict),
        avg_length,
        max_length,
        min_length,
        filename=file.name.split(".")[0],
    )

    return stats


def process_directory(
    directory: Path, filetype: str = ".fasta"
) -> dict[str, FileStats]:
    data: dict[str, FileStats] = {}

    for file in directory.glob(f"*{filetype}"):
        file_stats = get_stats_for_file(file)
        data[file_stats.filename] = asdict(file_stats)

    return data
