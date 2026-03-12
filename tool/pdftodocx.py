import sys
import argparse
import os
from pdf2docx import Converter

def convert_pdf_to_docx(pdf_file, docx_file):
    """
    Converts a PDF file to a DOCX file.
    """
    if not os.path.exists(pdf_file):
        print(f"Error: The file '{pdf_file}' does not exist.")
        return False

    try:
        print(f"Converting '{pdf_file}' to '{docx_file}'...")
        cv = Converter(pdf_file)
        cv.convert(docx_file) # all pages by default
        cv.close()
        print(f"Successfully converted '{pdf_file}' to '{docx_file}'.")
        return True
    except Exception as e:
        print(f"An error occurred during conversion: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Convert PDF to DOCX")
    parser.add_argument("input", nargs="?", help="Path to the input PDF file")
    parser.add_argument("-o", "--output", help="Path to the output DOCX file (optional)")

    args = parser.parse_args()

    pdf_path = args.input
    
    # If no input path is provided, ask for it
    if not pdf_path:
        pdf_path = input("Please enter the full path to the PDF file: ").strip()
        # Remove quotes if the user copied path with them
        pdf_path = pdf_path.strip('"').strip("'")

    if not pdf_path:
        print("Error: No input path provided.")
        return

    docx_path = args.output

    if not docx_path:
        # If no output path is provided, use the same name but with .docx extension
        base_name = os.path.splitext(pdf_path)[0]
        docx_path = f"{base_name}.docx"

    convert_pdf_to_docx(pdf_path, docx_path)

if __name__ == "__main__":
    main()
