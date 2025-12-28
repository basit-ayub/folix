import fitz
import argparse
import os
import re

fitz.TOOLS.mupdf_display_errors(False)

# Configuration: Titles containing these words will be skipped
BLOCKLIST = [ "half title","series page","title page","epilogue","cover","bibliography", "index", "contents", "preface", "acknowledgments", "copyright"]

def sanitize_filename(name):

    name = name.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    clean_name = re.sub(r'[\\/*?:"<>|]', "", name)
    clean_name = re.sub(r'[\x00-\x1f]', '', clean_name)
    clean_name = re.sub(r'\s+', ' ', clean_name)

    return clean_name.strip()


def extract_chapters(args):
    input_path = args.input_file
    output_dir = args.output_dir
    target_level = args.level

    try:
        doc = fitz.open(input_path)
        toc = doc.get_toc()

        if not toc:
            print("⚠️  No Table of Contents found.")
            return

        # ---------------------------------------------------------
        # 1. Analyze Hierarchy & Interactive Menu
        # ---------------------------------------------------------
        level_titles = {}
        for item in toc:
            lvl, title = item[0], item[1]
            if lvl not in level_titles: level_titles[lvl] = []
            level_titles[lvl].append(title)

        if target_level is None:
            print(f"\n📘  Analyzing structure of: {os.path.basename(input_path)}")
            print("-" * 80)
            print(f"{'Lvl':<4} | {'Count':<6} | {'Samples (First 3 items)'}")
            print("-" * 80)

            sorted_levels = sorted(level_titles.keys())
            for lvl in sorted_levels:
                titles = level_titles[lvl]
                count = len(titles)
                preview = ", ".join(titles[:3])
                if len(preview) > 55:
                    preview = preview[:52] + "..."
                elif count > 3:
                    preview += ", ..."
                print(f"{lvl:<4} | {count:<6} | {preview}")
            print("-" * 80)

            while True:
                user_input = input("\nSelect a Level to extract (or 'q' to quit): ").strip()
                if user_input.lower() == 'q': return
                if user_input.isdigit() and int(user_input) in level_titles:
                    target_level = int(user_input)
                    break
                else:
                    print("❌ Invalid level.")

        # ---------------------------------------------------------
        # 2. Preparation
        # ---------------------------------------------------------
        print(f"\n🚀 Extracting Level {target_level} (Including all sub-chapters)...")

        if not output_dir:
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            output_dir = f"{base_name}_chapters"
        if not os.path.exists(output_dir): os.makedirs(output_dir)

        # ---------------------------------------------------------
        # 3. Smart Extraction Logic
        # ---------------------------------------------------------
        # We walk through the TOC. When we find a target_level item,
        # we look forward until we hit another item of the SAME level (or higher).

        valid_chapters = []

        for i, item in enumerate(toc):
            lvl, title, start_page = item[0], item[1], item[2]

            # We only care if this item matches our target level
            if lvl != target_level:
                continue

            # Check Blocklist
            is_blocked = False
            for bad in BLOCKLIST:
                if re.search(r'\b' + re.escape(bad) + r'\b', title.lower()):
                    is_blocked = True
                    break
            if is_blocked:
                print(f"   Skipping ignored section: {title}")
                continue

            # --- CALCULATE END PAGE ---
            # Look ahead in the TOC starting from the *next* item
            end_page = len(doc)  # Default: End of book

            for j in range(i + 1, len(toc)):
                next_lvl = toc[j][0]
                next_page = toc[j][2]

                # We stop ONLY if we hit a sibling (Same Level) or a parent (Higher Level/Lower Number)
                # Example: We are Level 2. We stop at next Level 2 OR next Level 1.
                # We do NOT stop at Level 3, 4, 5 (children).
                if next_lvl <= target_level:
                    end_page = next_page - 1
                    break

            # Sanity Check
            if end_page < start_page: end_page = start_page

            valid_chapters.append({
                "title": title,
                "start": start_page,
                "end": end_page
            })

        print(f"   Found {len(valid_chapters)} valid chapters.\n")

        # ---------------------------------------------------------
        # 4. Save Files
        # ---------------------------------------------------------
        for i, chapter in enumerate(valid_chapters):
            safe_title = sanitize_filename(chapter['title'])
            out_name = f"{i + 1:02d}_{safe_title}.pdf"
            out_path = os.path.join(output_dir, out_name)

            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=chapter['start'] - 1, to_page=chapter['end'] - 1)
            new_doc.save(out_path)

            pg_count = (chapter['end'] - chapter['start']) + 1
            print(f"  Saved: {out_name} ({pg_count} pages)")

        print(f"\n✅ Done! Check the folder: /{output_dir}")

    except Exception as e:
        print(f"An error occurred: {e}")


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

    # ... inside main() ...

    parser_extract = subparsers.add_parser("extract", help="Auto-extract chapters")
    parser_extract.add_argument("input_file", help="Path to the PDF file")
    parser_extract.add_argument("--output-dir", "-d", help="Directory to save chapters")
    parser_extract.add_argument("--level", "-l", type=int, help="Which hierarchy level to extract (1=Part, 2=Chapter)")

    parser_extract.set_defaults(func=extract_chapters)

    args = parser.parse_args()

    # Execute the function associated with the chosen command
    args.func(args)


if __name__ == "__main__":
    main()