# InvoiceIntake_Demo

A classic RPA UiPath project demonstrating invoice processing automation.

## Project Structure

```
InvoiceIntake_Demo/
├── Main.xaml                          # Main orchestration workflow
├── Workflows/
│   ├── ExtractInvoice.xaml           # Extracts text from invoice PDFs
│   ├── ApplyPolicy.xaml              # Applies business rules to invoice data
│   └── WriteResult.xaml              # Writes processing results to output files
├── Data/
│   ├── Input/                        # Place invoice PDFs here
│   └── Output/                       # Processing results are written here
└── project.json

```

## Workflows

### Main.xaml
The main orchestration workflow that:
- Scans the `Data/Input` folder for PDF files
- Iterates through each PDF file
- Invokes the three sub-workflows in sequence
- Logs progress and completion status

### Workflows/ExtractInvoice.xaml
**Input:** `in_InvoiceFilePath` (String) - Path to the PDF file
**Output:** `out_InvoiceData` (String) - Extracted text content

Reads the invoice file and extracts text content. Includes error handling for file read failures.

### Workflows/ApplyPolicy.xaml
**Input:** `in_InvoiceData` (String) - Extracted invoice data
**Output:** `out_PolicyResult` (String) - Policy decision result

Applies business rules:
- Checks if extraction was successful
- Flags large invoices for review
- Determines approval status based on data quality

### Workflows/WriteResult.xaml
**Input:** 
- `in_FileName` (String) - Original file name
- `in_InvoiceData` (String) - Extracted data
- `in_PolicyResult` (String) - Policy result

Writes a formatted result file to `Data/Output` with:
- Processing timestamp
- Invoice data excerpt (first 200 characters)
- Policy decision result

## How to Run

1. **Add invoice files:**
   - Place PDF invoice files in `Data/Input/`
   - A sample text invoice is provided as reference

2. **Run the workflow:**
   - Open the project in UiPath Studio
   - Press F5 or click Run
   - The workflow will process all PDFs in the input folder

3. **Check results:**
   - Results are written to `Data/Output/`
   - Each processed file gets a `_result.txt` file with processing details

## Technical Details

- **Expression Language:** C#
- **Target Framework:** .NET Windows
- **Dependencies:** UiPath.System.Activities [26.2.4]

## Sample Output

```
=== INVOICE PROCESSING RESULT ===
File: sample_invoice.pdf
Timestamp: 2024-04-21 19:17:34
---
Invoice Data:
INVOICE #12345
==================

From: ABC Corporation
123 Business Street
New York, NY 10001
...
---
Policy Result:
Approved: True | Reason: Standard approval
===================================
```

## Notes

- The current implementation uses `ReadTextFile` which works with text files. For actual PDF processing, you would need to:
  - Install `UiPath.PDF.Activities` package
  - Replace the `ReadTextFile` activity with `Read PDF Text` or `Read PDF With OCR`
- Error handling is implemented at each stage
- All processing steps are logged for traceability
