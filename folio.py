import fitz  # PyMuPDF
import argparse

def split_pdf(args):

    input_path = args.input_file
    start_page = args.start
    end_page = args.end
    output_name = args.output

    try:
        src_doc = fitz.open(input_path)

        # Validation
        total_pages = len(src_doc)
        if start_page < 1 or end_page > total_pages:
            print(f"Error: Page range must be between 1 and {total_pages}.")
            return
        if start_page > end_page:
            print("Error: Start page cannot be greater than end page.")
            return

        new_doc = fitz.open()
        new_doc.insert_pdf(src_doc, from_page=start_page - 1, to_page=end_page - 1)

        # Naming logic
        if not output_name:
            output_name = f"split_{start_page}-{end_page}.pdf"

        if not output_name.lower().endswith(".pdf"):
            output_name += ".pdf"

        new_doc.save(output_name)
        print(f"Success! Created '{output_name}' with {len(new_doc)} pages.")

    except Exception as e:
        print(f"An error occurred: {e}")


def merge_pdf(args):

    input_files = args.input_files
    output_name = args.output

    if len(input_files) < 2:
        print("Error: You need at least 2 files to merge.")
        return

    try:
        merged_doc = fitz.open()

        # Loop through the variable list of files
        for file_path in input_files:
            print(f"Adding {file_path}...")
            doc = fitz.open(file_path)
            merged_doc.insert_pdf(doc)

        # Naming logic
        if not output_name:
            output_name = "merged_output.pdf"

        if not output_name.lower().endswith(".pdf"):
            output_name += ".pdf"

        merged_doc.save(output_name)
        print(f"Success! Merged {len(input_files)} files into '{output_name}'.")

    except Exception as e:
        print(f"An error occurred: {e}")


def main():
    parser = argparse.ArgumentParser(description="Folio: A tool to split and merge PDFs.")

    # 1. Create Subparsers (This creates the "split" and "merge" sub-commands)
    subparsers = parser.add_subparsers(dest="command", required=True, help="Choose a command")

    # --- SPLIT COMMAND ---
    # folio.py split input.pdf -s 1 -e 5
    parser_split = subparsers.add_parser("split", help="Split a PDF by page range")
    parser_split.add_argument("input_file", help="Path to the PDF file")
    parser_split.add_argument("--start", "-s", type=int, required=True, help="First page")
    parser_split.add_argument("--end", "-e", type=int, required=True, help="Last page")
    parser_split.add_argument("--output", "-o", help="Output filename")
    parser_split.set_defaults(func=split_pdf)

    # --- MERGE COMMAND ---
    # folio.py merge file1.pdf file2.pdf file3.pdf -o final.pdf
    parser_merge = subparsers.add_parser("merge", help="Merge multiple PDFs")
    # nargs='+' means "gather 1 or more arguments into a list"
    parser_merge.add_argument("input_files", nargs='+', help="List of PDF files to merge")
    parser_merge.add_argument("--output", "-o", help="Output filename")
    parser_merge.set_defaults(func=merge_pdf)

    args = parser.parse_args()

    # Execute the function associated with the chosen command
    args.func(args)


if __name__ == "__main__":
    main()