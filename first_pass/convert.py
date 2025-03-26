import csv
from os import path, mkdir
from re import split
from uuid import uuid4

if not path.exists("output"):
    mkdir("output")  # create directory if necessary

# Open the output files
with open("database_explorer.srt", "r") as input, open(
    path.join("output", "document.csv"), "w"
) as doc_output, open(path.join("output", "segment.csv"), "w") as seg_output, open(
    path.join("output", "token.csv"), "w"
) as tok_output, open(
    path.join("output", "token_form.csv"), "w"
) as form_output:

    # Write the headers in a CSV format
    doc_csv = csv.writer(doc_output)
    doc_csv.writerow(["document_id", "char_range"])
    seg_csv = csv.writer(seg_output)
    seg_csv.writerow(["segment_id", "char_range"])
    tok_csv = csv.writer(tok_output)
    tok_csv.writerow(["token_id", "form_id", "char_range", "segment_id"])
    form_csv = csv.writer(form_output)
    form_csv.writerow(["form_id", "form"])

    char_range = 1  # will be incremented with each character in a token
    token_id = 1  # will be incremented with each new token
    all_forms = {}  # stores the encountered forms along with their index
    while line := input.readline():
        line = line.strip()
        for segment in split(r"[.?!]", line):
            if not segment.strip():
                continue
            char_range_start_seg = char_range  # lower bound of the segment's char_range
            seg_id = uuid4()  # segments use UUIDs as their ID
            for token in split(r"[', ]", segment):
                form = token.strip()
                if not form:
                    continue
                # retrieve/store the form's index
                form_id = all_forms.get(form, len(all_forms) + 1)
                all_forms[form] = form_id
                tok_csv.writerow(
                    [
                        token_id,
                        form_id,
                        f"[{char_range},{char_range+len(form)})",
                        seg_id,
                    ]
                )
                char_range += len(form)  # increment char_range by the form's length
                token_id += 1  # increment by 1 for each processed token
            seg_csv.writerow([seg_id, f"[{char_range_start_seg},{char_range})"])
    # now write the lookup table
    for form, form_id in all_forms.items():
        form_csv.writerow([form_id, form])
    doc_csv.writerow(["1", f"[1,{char_range})"])
