import fitz
import argparse
import os
import re
import json
from mistralai import Mistral
fitz.TOOLS.mupdf_display_errors(False)

# List to remove unnecessary pages.
BLOCKLIST = [ "edition","appendix","references","half title","series page","title page","epilogue","cover","bibliography", "index", "contents", "preface", "acknowledgments", "copyright"]

def sanitize_filename(name):

    name = name.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    clean_name = re.sub(r'[\\/*?:"<>|]', "", name)
    clean_name = re.sub(r'[\x00-\x1f]', '', clean_name)
    clean_name = re.sub(r'\s+', ' ', clean_name)

    return clean_name.strip()

def get_most_common_size(doc):
    styles = {}
    for i in range(min(5, len(doc))):  # First 5 pages
        try:
            page = doc[min(i + 15, len(doc) - 1)]  # Avoid the initial front matter.
            blocks = page.get_text("dict")["blocks"]
            for b in blocks:
                if "lines" in b:
                    for line in b["lines"]:
                        for span in line["spans"]:
                            s = round(span["size"], 1)
                            styles[s] = styles.get(s, 0) + len(span["text"])
        except:
            continue

    if not styles: return 11.0   # default to 11
    return sorted(styles.items(), key=lambda x: x[1], reverse=True)[0][0]

def calculate_global_offset(doc, ai_toc):
    if not ai_toc: return 0

    # We use the first chapter as anchor
    first_ch_title = ai_toc[0][1]
    first_ch_page_ai = ai_toc[0][2]

    # Heuristics
    body_size = get_most_common_size(doc)
    threshold_size = body_size * 1.1  # Title must be >10% bigger than body

    #print(f"Calibrating offset (Searching for '{first_ch_title}')...")

    # Scan the first 50 pages for the visual title
    found_page_idx = -1

    for i in range(min(50, len(doc))):  # Search first 50 pages
        page = doc[i]

        # Optimization: Only look at top 50% of page
        rect = page.rect
        header_zone = fitz.Rect(0, 0, rect.width, rect.height * 0.6)

        # Get blocks in header zone
        blocks = page.get_text("dict", clip=header_zone)["blocks"]

        for b in blocks:
            if "lines" not in b: continue
            for line in b["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    size = span["size"]

                    if size > threshold_size:
                        # Simple fuzzy match
                        clean_title = re.sub(r'\d+', '', first_ch_title).strip().lower()
                        clean_text = re.sub(r'\d+', '', text).strip().lower()

                        # Check for at least 4 chars
                        if len(clean_title) > 4 and clean_title in clean_text:
                            found_page_idx = i + 1  # +1 for 1-based indexing
                            break

                        # Reverse check
                        if len(clean_text) > 4 and clean_text in clean_title:
                            found_page_idx = i + 1
                            break

            if found_page_idx != -1: break
        if found_page_idx != -1: break

    if found_page_idx != -1:
        # Calculate Offset
        offset = found_page_idx - first_ch_page_ai
       # print(f"      -> Found visual match on PDF Page {found_page_idx}.")
       # print(f"      -> Calculated Offset: {offset} pages.")
        return offset
    else:
        print(f"Could not visually verify start page. Assuming Offset 0.")
        return 0

def get_physical_text(page):

    blocks = page.get_text("dict")["blocks"]
    all_spans = []

    for b in blocks:
        if "lines" in b:
            for l in b["lines"]:
                for s in l["spans"]:
                    all_spans.append(s)

    if not all_spans: return ""

    #sort by x-axis
    all_spans.sort(key=lambda s: (round(s["origin"][1]), s["origin"][0]))

    lines = []
    current_line = [all_spans[0]]

    for span in all_spans[1:]:
        # If vertical position is close (within 5 pixels), it's the same line
        prev_y = current_line[-1]["origin"][1]
        curr_y = span["origin"][1]

        if abs(curr_y - prev_y) < 5:   #proximity heuristic
            current_line.append(span)
        else:
            # New line detected
            lines.append(current_line)
            current_line = [span]
    lines.append(current_line)

    # Join
    final_output = []
    for line_spans in lines:
        # Sort left-to-right within the line just to be safe
        line_spans.sort(key=lambda s: s["origin"][0])
        text_line = " ".join([s["text"].strip() for s in line_spans])
        final_output.append(text_line)

    return "\n".join(final_output)

def get_toc_text_from_pdf(doc):
    start_page = -1

    # search in first 20 pages
    for i in range(min(20, len(doc))):

        page_text = doc[i].get_text().lower()
        if "contents" in page_text[:800] or "index" in page_text[:500]:
            start_page = i
            #print(f"   found 'Contents' text on page {i + 1}...")
            break

    if start_page == -1: return None

    # 2. Extract using physical extraction
    full_text = ""
    pages_to_scan = 10

    for i in range(start_page, min(start_page + pages_to_scan, len(doc))):
        text = get_physical_text(doc[i])

        filtered_lines = []
        for line in text.split('\n'):
            line = line.strip()
            if not line: continue

            # keep lines that have a number at end (chapter name ------ page number)
            if re.search(r'(\d+|[ivxlc]+)$', line.lower()):
                filtered_lines.append(line)
            elif len(line) < 80 and line.isupper():
                filtered_lines.append(line)

        full_text += f"\n--- PDF Page {i + 1} ---\n"
        full_text += "\n".join(filtered_lines)

    return full_text

def generate_toc_with_mistral(toc_text):
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        #print("Error: MISTRAL_API_KEY environment variable not set.")
        return None

    #print("Sending text to Mistral AI for analysis...")

    try:
        client = Mistral(api_key=api_key)

        prompt = f"""
        You are a PDF parsing assistant. I will provide text from a book's Table of Contents.
        Extract the Chapter Titles and their Starting Page Numbers.

        Rules:
        1. Return ONLY a valid JSON list. Do not include markdown formatting (like ```json).
        2. JSON Format: [{{"title": "Chapter Name", "page": 15}}, {{"title": "Next Chapter", "page": 20}}]
        3. Convert Roman Numerals (ix, x) to integers if possible, or ignore them if they are just front-matter.
        4. Do not invent page numbers. If a page number is missing, skip that chapter.
        5. Ignore "Preface", "Foreword", "Index" if they don't seem like main chapters.
        6. Do NOT include any starting lines explaining the output. Provide only the json list.

        Here is the raw text:
        {toc_text}
        """

        chat_response = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        response_content = chat_response.choices[0].message.content.strip()
        if response_content.startswith("```"):
            response_content = response_content.split("```")[1]
        if response_content.startswith("json"):
            response_content = response_content[4:]
        data = json.loads(response_content)

        formatted_toc = []
        for item in data:
            formatted_toc.append([1, item['title'], int(item['page'])])

        return formatted_toc

    except Exception as e:
        print(f"Mistral Parsing failed: {e}")
        return None


def extract_chapters(args):
    input_path = args.input_file
    output_dir = args.output_dir
    target_level = args.level

    try:
        doc = fitz.open(input_path)
        toc = doc.get_toc()
        #toc = []

        # if no TOC use Mistral API
        if not toc:
            print("No Metadata Table of Contents found.")
            print("Attempting AI extraction via Mistral API...")

            raw_toc_text = get_toc_text_from_pdf(doc)

            if raw_toc_text:
                ai_toc = generate_toc_with_mistral(raw_toc_text)

                if ai_toc:
                    print(f"Mistral successfully identified {len(ai_toc)} chapters.")
                    offset = calculate_global_offset(doc, ai_toc)

                    # Apply offset to all chapters
                    adjusted_toc = []
                    for item in ai_toc:
                        lvl, title, page_num = item
                        new_page = page_num + offset
                        adjusted_toc.append([lvl, title, new_page])

                    toc = adjusted_toc
                    target_level = 1
                else:
                    print("Mistral could not parse the content.")
                    return

        # Interactive menu for TOC extraction
        level_titles = {}
        for item in toc:
            lvl, title = item[0], item[1]
            if lvl not in level_titles:
                level_titles[lvl] = []
            level_titles[lvl].append(title)

        if target_level is None:
            print(f"\nAnalyzing structure of: {os.path.basename(input_path)}")
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
                if user_input.lower() == 'q':
                    return
                if user_input.isdigit() and int(user_input) in level_titles:
                    target_level = int(user_input)
                    break
                else:
                    print("❌ Invalid level.")


        print(f"\nExtracting Level {target_level} ...")

        if not output_dir:
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            output_dir = f"{base_name}_chapters"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        valid_chapters = []

        for i, item in enumerate(toc):
            lvl, title, start_page = item[0], item[1], item[2]

            # only cater to selected level
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

                # We stop ONLY if we hit a same level or higher

                if next_lvl <= target_level:
                    end_page = next_page - 1
                    break

            # Sanity Check
            if end_page < start_page:
                end_page = start_page

            valid_chapters.append({
                "title": title,
                "start": start_page,
                "end": end_page
            })

        print(f"   Found {len(valid_chapters)} valid chapters.\n")

        # Save files

        for i, chapter in enumerate(valid_chapters):
            safe_title = sanitize_filename(chapter['title'])
            out_name = f"{i + 1:02d}_{safe_title}.pdf"
            out_path = os.path.join(output_dir, out_name)

            new_doc = fitz.open()

            # Use the context manager to silence warnings
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

    # Subparsers
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