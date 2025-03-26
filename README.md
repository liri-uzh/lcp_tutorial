# Resources for the LCP tutorials

This repository hosts scripts and resources for the tutorials on LCP.

## Import tutorial

The four folders below concern the [LCP import tutorial](https://lcp.linguistik.uzh.ch/manual/import_tutorial.html). Each contains a python script file, and any necessary .srt file, but no media file.

### first_pass

This folder contains one .srt file and a preliminary script file that outputs off-target .csv files.

### text_no_lemma

This folder contains the two .srt files of the import tutorial and a refactored script file that fixes the issues from first_pass. The output is not ready for upload to LCP.

### text_with_lemma

This folder contains the two .srt files of the import tutorial, a JSON configuration file and a script that includes additional annotations and outputs .csv files which, when supplemeted with the configuration file, are ready for upload to LCP.

### video

This folder contains the two .srt files of the import tutorial, a JSON configuration file and a script that incorporates time alignment and references to MP4s in the output .csv files. It does _not_ contain the referenced video files: those need to be separately procured and placed inside a _media_ subfolder, created in the folder that contains the output .csv files and the .json configuration file, before the data can be uploaded to LCP.