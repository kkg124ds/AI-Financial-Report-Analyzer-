# AI Financial Report Analyzer

A small, explainable NLP project that helps an analyst review a financial report faster. Upload a selectable-text PDF or UTF-8 text file to receive an extractive summary, selected year-over-year metric comparisons, and risk or opportunity cues with page references and supporting text.

This project is designed as an interview portfolio prototype. It shows document handling, NLP, rule-based financial analysis, evidence traceability, and a simple Streamlit interface without requiring an API key.

## Problem

Reading a long annual or quarterly report takes time. An analyst often needs to find the executive highlights, compare key metrics, and identify disclosures that deserve closer review.

## What the app does

1. Reads text from a PDF or `.txt` file and keeps page numbers.
2. Uses TF-IDF sentence ranking to select relevant report sentences for a concise **extractive** summary. The sentences come from the report; the app does not invent new summary text.
3. Looks for a short list of financial metrics and compares the first two values found on the same metric row.
4. Applies visible rules to flag changes such as declining revenue, rising debt, or improving operating cash flow.
5. Searches for selected risk and opportunity phrases and shows the source sentence for human review.
6. Lets the user download the result as JSON.

## Example workflow

```text
PDF or TXT → extract text by page → rank sentences → parse metric rows
                                       ↓
                           apply review rules + show evidence
```

## Project files

```text
ai-financial-report-analyzer/
├── app.py                 # Streamlit upload page and analysis results
├── analyzer.py            # PDF/text extraction, TF-IDF summary, metric rules
├── sample_report.txt      # Fictional report for trying the app
├── requirements.txt       # Python dependencies
├── .gitignore             # Local environment and generated files to ignore
└── README.md              # Project documentation
```

## Run on Windows

Install Python 3.10 or newer and VS Code with the Microsoft Python extension. Open this folder in VS Code, then choose **Terminal → New Terminal**.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

If `py` is not recognized, use `python` to create the environment. The project-specific `.venv` Python path shown above is for Windows PowerShell.

## Run on macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

When Streamlit starts, open the local address printed in the terminal. Upload the included `sample_report.txt` first. It is fictional and exists only to demonstrate the app.

## Metrics currently recognized

The first version checks for these labels (common wording variants are included in the code):

- Revenue / net sales
- Net income / net profit
- Operating income / operating profit
- Operating cash flow
- Total debt / borrowings
- Cash and cash equivalents

For a comparison, the app expects two values on the same extracted text line. It uses the first and second values in report order and extracts fiscal years where present. Always compare the displayed evidence with the original report. Financial statements often have layouts that PDF text extraction cannot preserve perfectly.

## How the analysis works

### Extractive summary

The app splits extracted text into sentences, converts them to TF-IDF features with scikit-learn, ranks sentences by their weighted terms, and returns the top sentences in their original order. Each sentence includes a page number. This is extractive NLP, not a large language model, and it avoids generating unsupported prose.

### Metrics and changes

Metric rows are located with regular expressions. When two amounts are found, the app calculates percentage change:

```text
percentage change = (latest value - prior value) / |prior value| × 100
```

Simple thresholds flag changes for review. For example, revenue down by at least 5% or total debt up by at least 10% creates a review signal. These thresholds are demonstration rules, not universal finance standards.

### Disclosure cues

The app looks for selected phrases such as “going concern,” “material weakness,” “supply chain disruption,” “new contract,” and “capacity expansion.” It displays the sentence containing a match. A phrase match is a prompt for a person to inspect the text, not a conclusion about the company.

## Design choices to discuss in an interview

- **Traceability:** Each extracted summary sentence and metric row links back to a page and source text.
- **No external AI service:** The project runs without paid API access or a secret key.
- **Explainable first version:** TF-IDF and explicit thresholds are easy to inspect and challenge.
- **Human review:** The app highlights passages and changes; an analyst decides what they mean.
- **Separation of concerns:** `analyzer.py` contains analysis functions; `app.py` handles the UI.

## Limitations

- Scanned PDFs need OCR; OCR is not included.
- PDF text extraction order and table layout vary by source. Some metrics may be missed or parsed incorrectly.
- Metric recognition requires a supported label and usually two values on the same line. The user must verify the quoted source line and units.
- A keyword can appear in a negated or historical sentence. The app does not understand context deeply.
- The thresholds are illustrative and have not been validated against analyst decisions or investment outcomes.
- The project does not assess whether a company is a good investment, forecast returns, or replace an accountant, auditor, or financial adviser.

## Responsible use and privacy

The app makes no API calls and analyzes files in the local Streamlit process. Do not upload confidential reports to a hosted version unless you have approval and have reviewed the host’s data handling. Treat all signals as prompts for human review.

## Suggested next steps

1. Add tests with sample reports that include missing values, negative numbers, multiple currencies, and alternate metric labels.
2. Add OCR for scanned reports and table extraction for complex financial statements.
3. Add a benchmark set of manually checked reports and measure extraction precision and recall.
4. Add an optional LLM summary only after preserving source citations and checking every generated claim against the report.
5. Add multi-year trends and segment-level comparisons after validating the parser.

## Interview explanation

> “I built a document-analysis prototype to reduce the time spent triaging financial reports. It extracts PDF text with page references, uses TF-IDF to select report sentences for an extractive summary, parses a small set of financial metrics, and applies transparent rules to flag changes such as falling revenue or rising debt. I include the source sentence and page so an analyst can verify each finding. The first version is intentionally narrow: PDF table layouts vary, so metric extraction needs validation, and the signals support human review rather than investment decisions.”

## Technologies

- Python
- Streamlit
- PyMuPDF
- pandas
- scikit-learn (`TfidfVectorizer`)

## References

- [Streamlit file uploader](https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader)
- [PyMuPDF text extraction](https://pymupdf.readthedocs.io/en/latest/recipes-text.html)
- [scikit-learn TfidfVectorizer](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html)
