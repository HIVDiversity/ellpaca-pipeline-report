import enum
import os
from pathlib import Path
from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
from attrs import asdict, define
from Bio import SeqIO
from loguru import logger
from typing_extensions import Optional


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


class SampleIDSchema(enum.Enum):
    ELLPACA = "ELLPACA"


def get_file_info_from_name(
    file: Path, pipeline_point: Optional[str]
) -> SequencingFile:
    file_name = file.stem
    participant_id = file_name.split("_")[0]
    visit_id = file_name[7:11]
    # pool_id = file_name.split("-")[1].split(".").get(0)

    return SequencingFile(
        name=file_name.split(".")[0],
        pool="",
        visit=visit_id,
        participant=participant_id,
        path=file,
        pipeline_point=pipeline_point,
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
    if not sequencing_file:
        sequencing_file: SequencingFile = SequencingFile(
            name=name,
            pool=pool,
            visit=visit,
            participant=participant,
            path=file,
            pipeline_point=sequencing_timepoint,
        )

    if os.stat(file).st_size == 0:
        return [
            Sequence(
                name=None,
                length=None,
                pool=sequencing_file.pool,
                visit=sequencing_file.visit,
                participant=sequencing_file.participant,
                path=sequencing_file.path,
                pipeline_point=sequencing_file.pipeline_point,
                filename=sequencing_file.name,
            )
        ]
    reader = SeqIO.parse(file.open("r", encoding="utf-8"), "fasta")

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


def msa_to_numpy(msa_file: Path):
    """Reads a multiple sequence alignment into a numpy array"""
    msa_array = []
    seq_names = []

    reader = SeqIO.parse(msa_file, "fasta")

    for record in reader:
        new_seq = []

        for char in record.seq:
            new_seq.append(ord(char))

        msa_array.append(new_seq)
        seq_names.append(record.id)

    msa_np = np.asarray(msa_array)

    return seq_names, msa_np
