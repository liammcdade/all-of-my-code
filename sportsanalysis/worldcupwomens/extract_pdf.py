from pypdf import PdfReader
import os

pdf_path = r'c:\Users\liam\Documents\GitHub\All-code-in-one\sportsanalysis\worldcupwomens\Women\'s World Cup 2027 Qualification Analysis.pdf'
# Wait, let's list the directory again to be sure of the exact filename
# or use os.path.join
target_dir = r'c:\Users\liam\Documents\GitHub\All-code-in-one\sportsanalysis\worldcupwomens'
files = os.listdir(target_dir)
pdf_file = [f for f in files if f.endswith('.pdf') and '2027' in f][0]
full_path = os.path.join(target_dir, pdf_file)

import sys

# Set stdout to use utf-8
sys.stdout.reconfigure(encoding='utf-8')

reader = PdfReader(full_path)
for i, page in enumerate(reader.pages):
    print(f"--- Page {i+1} ---")
    text = page.extract_text()
    if text:
        print(text)
