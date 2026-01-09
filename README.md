# Folix ✂️

**A smart, AI-powered PDF splitter.**

Folix is a CLI tool designed to split large PDF textbooks and documents into clean, individual chapter files. Unlike standard splitters that blindly cut pages, Folix uses **Mistral AI** to parse the Table of Contents, automatically calculate page offsets, and handle complex layouts (like double‑column indices) with ease.

---

## 🚀 Features

* 📚 **Smart Chapter Extraction**
  Automatically detects chapters using native PDF bookmarks (ToC).

* 🤖 **AI‑Powered Fallback**
  If bookmarks are missing, Folix reads the visual *Table of Contents* page and uses Mistral AI to identify chapters.

* 🧠 **Intelligent Offset Calculation**
  Automatically aligns printed page numbers  with the physical PDF structure .

* 👁️ **Physical Layout Analysis**
  Correctly parses multi‑column Tables of Contents that confuse standard PDF tools.

* 🔍 **Interactive Inspection**
  Visualizes the document structure so you can choose exactly which hierarchy level (Part, Chapter, Section) to extract.

* 🛠️ **Zero‑Config CLI**
  Simple commands for extracting, merging, and inspecting PDFs.

---

## 📦 Installation

### Option A: Install via PyPI (Recommended)

```bash
pip install folix
```

### Option B: Install from Source

```bash
git clone https://github.com/yourusername/folix.git
cd folix
pip install .
```

---

## 🔑 Setup (AI Features)

Folix works out‑of‑the‑box for PDFs that include standard bookmarks. For scanned books or files without metadata, you’ll need a **free Mistral AI API key** to enable automatic chapter detection.

### 1. Get an API Key

Sign up at **[https://console.mistral.ai](https://console.mistral.ai)** (generous free tier available).

### 2. Set the Environment Variable

**Mac / Linux**

```bash
export MISTRAL_API_KEY="your_actual_key_here"
```

**Windows (PowerShell)**

```powershell
$env:MISTRAL_API_KEY="your_actual_key_here"
```

---

## 📖 Usage

### 1. Extract Chapters

The primary command. Folix first attempts bookmark‑based extraction; if none are found, it automatically falls back to AI detection.

```bash
folix extract <file_name>
```

**Options:**

* `--level 1` → Extract top‑level items (e.g. *Parts*)
* `--level 2` → Extract chapters

---

### 2. Interactive Mode

If you’re unsure how the document is structured, run extraction normally and Folix will guide you.

```bash
folix extract <file_name>
```

**Example Output:**

```text
📘  Analyzing structure of: complex_book.pdf
--------------------------------------------------------------------------------
Lvl  | Count  | Samples (First 3 items)
--------------------------------------------------------------------------------
1    | 5      | Part I, Part II, Part III...
2    | 32     | 1. Introduction, 2. The Basics, 3. Advanced Topics...
--------------------------------------------------------------------------------

Select a Level to extract (or 'q' to quit):
```

---

### 3. Merge PDFs

Combine multiple PDFs into a single file.

```bash
folix merge <pdf_names> -output <output_file_name>
```

---
### 4. Manual Split
Split a page range manually.
```bash
folix split input.pdf --start <start_page> --end <end_page> --output <output_file_name> 
```

---

## 🛠️ How It Works

Folix uses a **three‑stage fallback system** to ensure accurate chapter extraction:

1. **Metadata Scan**
   Detects native PDF bookmarks (Table of Contents).

2. **AI Analysis**
   If metadata is missing, Folix locates the visual *Contents* page, cleans the extracted text to reduce token usage, and sends it to Mistral AI for chapter identification.

3. **Visual Anchor & Offset Alignment**

   * The AI may say: *"Chapter 1 starts on page 1"*
   * Folix scans the PDF to find where *"Chapter 1"* physically appears (e.g. page 18)
   * A global offset is calculated and applied to all chapters, ensuring precise cuts

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create your feature branch:

   ```bash
   git checkout -b feature/amazing-feature
   ```
3. Commit your changes:

   ```bash
   git commit -m "Add some amazing feature"
   ```
4. Push to the branch:

   ```bash
   git push origin feature/amazing-feature
   ```
5. Open a Pull Request

---

## 📄 License

Distributed under the **MIT License**. See ```LICENSE```
