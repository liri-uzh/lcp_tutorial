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


# helpler method returning frame_range/char_range in the proper format
def to_range(lower, upper):
    return f"[{lower},{upper})"


# custom class that will process and write the files
class Converter:

    # pass the output files + headers as keys, e.g. document=(doc_file,["document_id","char_range"])
    def __init__(self, **kwargs):
        self.char_range = 1  # incremented with each character of a token
        self.frame_offset = 0  # offset for the timestamps of the next document
        self.last_timestamps = (0, 0)  # last processed timestamp
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
            "original": {},
        }
        # the CSV outputs
        self.outputs = {
            filename: csv_writer(file, headers)
            for filename, (file, headers) in kwargs.items()
        }

    # helper method to convert hh:mm:ss,sss into a number (25fps)
    def timestamp_to_range(self, timestamp: str) -> int:
        hour, minute, second = timestamp.split(":")
        seconds = (
            float(second.replace(",", "."))
            + float(minute) * 60.0
            + float(hour) * 3600.0
        )
        return self.frame_offset + int(seconds * 25.0)

    # helper method that writes to the segment and token files
    def process_segment(self, text, frame_range_seg_start):
        text = text.strip()
        if not text:  # ignore this segment if it is empty
            return
        forms = self.lookups["form"]
        # lower bound of the segment's char_range
        char_range_seg_start = self.char_range
        seg_id = uuid4()  # use a uuid for the segment
        token = ""  # string buffer for the token being currently processed
        shortened = False  # is the current token preceded by a single-quote character?
        # read the text one character at a time (make sure it ends with a token delimiter)
        for c in text + ",":
            # if we hit a token delimiter: write the current token (if any)
            if search(self.token_delimiters, c):
                if not token:
                    continue
                # retrieve and store the form's ID
                form_id = forms.get(token, len(forms) + 1)
                forms[token] = form_id
                # write the token's information to the output
                self.outputs["token"].writerow(
                    [
                        self.token_id,
                        form_id,  # we use the same values for form
                        form_id,  # as for lemma
                        "yes" if shortened else "no",
                        to_range(self.char_range, self.char_range + len(token)),
                        seg_id,
                    ]
                )
                # increment the char_range counter by the number of characters in the token
                self.char_range += len(token)
                self.token_id += 1
                # if the token delimiter is a single quote, mark the next token as shortened
                shortened = c == "'"
                token = ""
            else:
                token += c  # append the character to the string buffer
        originals = self.lookups["original"]
        # retrieve and store the original text's ID
        original_id = originals.get(text, len(originals) + 1)
        originals[text] = original_id
        frame_range_seg_start = (
            frame_range_seg_start
            if self.last_timestamps[1] > frame_range_seg_start
            else frame_range_seg_start + 1
        )
        # now that all the tokens have been processed, write the segment to the segment file
        self.outputs["segment"].writerow(
            [
                seg_id,
                to_range(char_range_seg_start, self.char_range),
                to_range(frame_range_seg_start, self.last_timestamps[1]),
                original_id,
            ]
        )
        return

    # This will be called on each input file
    def process_document(self, file):
        char_range_doc_start = self.char_range  # lower bound of doc's char_range
        frame_range_doc_start = self.frame_offset  # lower bound of doc's frame_range
        current_segment = ""  # buffer storing the curent sentence's text
        frame_range_seg_start = self.frame_offset
        new_block = True  # are we starting a new block from the transcription file?
        while line := file.readline():
            if new_block:
                # in SRT files, at the start of a new block, the first two lines
                # are the block number and the timestamps: we skip both of those
                timestamp_string = file.readline().strip()
                self.last_timestamps = tuple(
                    [
                        self.timestamp_to_range(x)
                        for x in timestamp_string.split(" --> ")
                    ]
                )
                if not current_segment:
                    frame_range_seg_start = self.last_timestamps[0]
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
                self.process_segment(current_segment, frame_range_seg_start)
                # now process any remaining content
                current_segment = ""
                for middle_segment in remainder[1:-1]:
                    # the line could have full segments in the middle, as in "ipsum. lorem ipsum. lorem"
                    # if it does, call process_segment on each of those middle chunks
                    self.process_segment(middle_segment, frame_range_seg_start)
                # start a new current_segment with the last tokens in the line
                current_segment = remainder[-1]
                if search(self.segment_delimiters + "$", line):
                    # but if the line actually *ends* with a segment delimiter,
                    # call process_segment on the last tokens and start afresh
                    self.process_segment(current_segment, frame_range_seg_start)
                    current_segment = ""
        self.frame_offset = self.last_timestamps[1]
        filename_no_ext = file.name.replace(".srt", "")
        # we are done with the current document: write it to the document file
        self.outputs["document"].writerow(
            [
                self.document_id,
                to_range(char_range_doc_start, self.char_range),
                to_range(frame_range_doc_start, self.frame_offset),
                filename_no_ext,  # the name of the document
                '{"video": "' + filename_no_ext + '.mp4"}',  # the video file
            ]
        )
        # increment the counter for the next document
        self.document_id += 1
        return

    # called at the end: write the lookup files
    def write_lookups(self):
        for form, form_id in self.lookups["form"].items():
            self.outputs["token_form"].writerow([form_id, form])
            self.outputs["token_lemma"].writerow([form_id, form])
        for original, original_id in self.lookups["original"].items():
            self.outputs["segment_original"].writerow([original_id, original])
        return


# create the output folder if it doesn't exist yet
if not path.exists("output"):
    mkdir("output")

# we first create all the output files
with open(path.join("output", "document.csv"), "w") as doc_output, open(
    path.join("output", "segment.csv"), "w"
) as seg_output, open(
    path.join("output", "segment_original.csv"), "w"
) as original_output, open(
    path.join("output", "token.csv"), "w"
) as tok_output, open(
    path.join("output", "token_form.csv"), "w"
) as form_output, open(
    path.join("output", "token_lemma.csv"), "w"
) as lemma_output:

    # initiate an instance of Converter with the output files
    converter = Converter(
        document=(
            doc_output,
            ["document_id", "char_range", "frame_range", "name", "media"],
        ),
        segment=(
            seg_output,
            ["segment_id", "char_range", "frame_range", "original_id"],
        ),
        token=(
            tok_output,
            [
                "token_id",
                "form_id",
                "lemma_id",
                "shortened",
                "char_range",
                "segment_id",
            ],
        ),
        segment_original=(original_output, ["original_id", "original"]),
        token_form=(form_output, ["form_id", "form"]),
        token_lemma=(lemma_output, ["lemma_id", "lemma"]),
    )

    # now process each document
    for document in documents:
        with open(document, "r") as doc_file:
            converter.process_document(doc_file)

    # finally, create the lookup files
    converter.write_lookups()
