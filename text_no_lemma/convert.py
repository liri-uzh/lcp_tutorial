import csv

from os import path, mkdir
from re import search, split
from uuid import uuid4

documents = ["database_explorer.srt", "presenter_pro.srt"]  # the documents to process


# helper method to return a new CSV writer after writing the headers
def csv_writer(file, headers):
    writer = csv.writer(file)
    writer.writerow(headers)
    return writer


# helpler method returning char_range in the proper format
def to_range(lower, upper):
    return f"[{lower},{upper})"


# custom class that will process and write the files
class Converter:

    # pass the output files + headers as keys, e.g. document=(doc_file,["document_id","char_range"])
    def __init__(self, **kwargs):
        self.char_range = 1  # incremented with each character of a token
        self.document_id = 1  # incremented with each document
        self.token_id = 1  # increment with each token
        self.token_delimiters = (
            r"[', ]"  # the characters that separate tokens in the input
        )
        self.segment_delimiters = (
            r"[.?!]"  # the characters that mark the end of a segment in the input
        )
        # associate the unique values to IDs for lookup purposes
        self.lookups = {
            "form": {},
        }
        # the CSV outputs
        self.outputs = {
            filename: csv_writer(file, headers)
            for filename, (file, headers) in kwargs.items()
        }

    # helper method that writes to the segment and token files
    def process_segment(self, text):
        text = text.strip()
        if not text:  # ignore this segment if it is empty
            return
        forms = self.lookups["form"]
        # lower bound of the segment's char_range
        char_range_seg_start = self.char_range
        seg_id = uuid4()  # use a uuid for the segment
        # read the text one token at a time
        for token in split(self.token_delimiters, text):
            if not token:
                continue
            # retrieve and store the form's ID
            form_id = forms.get(token, len(forms) + 1)
            forms[token] = form_id
            # write the token's information to the output
            self.outputs["token"].writerow(
                [
                    self.token_id,
                    form_id,
                    to_range(self.char_range, self.char_range + len(token)),
                    seg_id,
                ]
            )
            # increment the char_range counter by the number of characters in the token
            self.char_range += len(token)
            self.token_id += 1
        # now that all the tokens have been processed, write the segment to the segment file
        self.outputs["segment"].writerow(
            [
                seg_id,
                to_range(char_range_seg_start, self.char_range),
            ]
        )
        return

    # This will be called on each input file
    def process_document(self, file):
        char_range_doc_start = self.char_range  # lower bound of doc's char_range
        current_segment = ""  # buffer storing the curent sentence's text
        new_block = True  # are we starting a new block from the transcription file?
        while line := file.readline():
            if new_block:
                # in SRT files, at the start of a new block, the first two lines
                # are the block number and the timestamps: we skip both of those
                file.readline()
                new_block = False
                continue
            if line == "\n":
                # in SRT files, an empty line signals the start of a new block
                new_block = True
                continue
            # from here on out we the line contains some actual transcript
            line = line.rstrip()
            if not search(self.segment_delimiters, line):
                # if the line has no segment delimiter, add it to the current segment
                current_segment += " " + line
            else:
                # if there's at least one segment delimiter, proceed in two times:
                # first end the current segment, then process the remainder content
                end_of_current_segment, *remainder = split(
                    self.segment_delimiters, line
                )
                current_segment += " " + end_of_current_segment
                # call process_segment now to write the current segment and its tokens to the files
                self.process_segment(current_segment)
                # now process any remaining content
                current_segment = ""
                for middle_segment in remainder[1:-1]:
                    # the line could have full segments in the middle, as in "ipsum. lorem ipsum. lorem"
                    # if it does, call process_segment on each of those middle chunks
                    self.process_segment(middle_segment)
                # start a new current_segment with the last tokens in the line
                current_segment = remainder[-1]
                if search(self.segment_delimiters + "$", line):
                    # but if the line actually *ends* with a segment delimiter,
                    # call process_segment on the last tokens and start afresh
                    self.process_segment(current_segment)
                    current_segment = ""
        # we are done with the current document: write it to the document file
        self.outputs["document"].writerow(
            [
                self.document_id,
                to_range(char_range_doc_start, self.char_range),
            ]
        )
        # increment the counter for the next document
        self.document_id += 1
        return

    # called at the end: write the lookup files
    def write_lookups(self):
        for form, form_id in self.lookups["form"].items():
            self.outputs["token_form"].writerow([form_id, form])
        return


# create the output folder if it doesn't exist yet
if not path.exists("output"):
    mkdir("output")

# we first create all the output files
with open(path.join("output", "document.csv"), "w") as doc_output, open(
    path.join("output", "segment.csv"), "w"
) as seg_output, open(path.join("output", "token.csv"), "w") as tok_output, open(
    path.join("output", "token_form.csv"), "w"
) as form_output:

    # initiate an instance of Converter with the output files
    converter = Converter(
        document=(doc_output, ["document_id", "char_range"]),
        segment=(seg_output, ["segment_id", "char_range"]),
        token=(
            tok_output,
            [
                "token_id",
                "form_id",
                "char_range",
                "segment_id",
            ],
        ),
        token_form=(form_output, ["form_id", "form"]),
    )

    # now process each document
    for document in documents:
        with open(document, "r") as doc_file:
            converter.process_document(doc_file)

    # finally, create the lookup files
    converter.write_lookups()
