#set page(
  paper: "a4",
  margin: (x: 1cm, y: 1cm),
)
#set text(font: "Noto Sans", size: 12pt)
#set table(
  stroke: (x, y) => if y == 0 {
    (bottom: 0.7pt + black)
  },
  align: (x, y) => (
    if x > 0 { center }
    else { left }
  )
)
#show link: underline
#let data = json("data/data.json")


#align(center)[
  #set text(size:20pt, weight: "bold")
  #data.run_name - Report

  #set text(size:14pt, weight: "medium", fill: gray)
  nf-codon-align

]
= Pipeline Information
Git Commit: #data.git_commit_hash

Version: x.y.z




= Overview
This pipeline run contained *#data.file_count_pre* files. *#data.file_count_post* files made it through the pipeline. We lost *#data.seq_count_lost* sequences, representing *#data.pct_seqs_lost*% of all sequences.

#align(center)[
  #table(align: (left+horizon, center+horizon), 
        columns: (4cm, 8cm),
        rows: 0.8cm,
        table.header([*Pipeline Point*], [*Sequence Count*]),
        [Pre], [#data.seq_count_pre],
        [Post], [#data.seq_count_post]
  ) 
]

== Sequence Loss Overview
This plot is an #link("https://upset.app/")[UpSet] plot, which indicates the various reasons why sequences were lost from the pipeline. A circle is *filled in* if that test was passed.
#image(data.img_upset_plot_path)

== Sequence Length
This plot shows the sequence length distribution for the sequences *that pass filter*.
#image(data.img_length_boxplot_path)

#block(breakable: false,
[
  = Alignment Quality Overview
  
#image(data.img_msa_grid_path)
]

)
= Pipeline Run Info
The following table shows the parameters that were used to run this pipeline version.

#data.nf_param_dump