import streamlit as st
import os
import google.generativeai as genai
from dotenv import load_dotenv
import PyPDF2

# --- SECURITY CONSTANTS ---
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_PDF_PAGES = 80

# Load environment variables securely
load_dotenv()
client = genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# --- FRONTEND UI SETUP ---
st.set_page_config(page_title="AI Legal Document Summarizer", page_icon="⚖️", layout="centered")

st.title("AI Legal Document Summarizer")
st.markdown("Extract core clauses from legal contracts. **Choose your input method below.**")

# --- AI LOGIC (Powered by Gemini) ---
def summarize_contract(text):
    system_prompt = """
    You are an expert Legal AI Assistant. 
    Analyze the provided legal document and extract ONLY the following:
    1. Parties Involved
    2. Governing Law
    3. Termination Conditions
    4. Financial Penalties (if any)
    
    Format the output as a clean Markdown bulleted list. Provide small description and give reference from the file.
    Do not hallucinate. If a clause is missing, write "Not specified in document."
    """

    # THE FIX: We combine the instructions and the document into one giant prompt
    full_prompt = system_prompt + "\n\n--- LEGAL DOCUMENT ---\n\n" + text

    try:
        # 1. Initialize model WITHOUT the system_instruction parameter
        model = genai.GenerativeModel('gemini-2.5-flash')

        # 2. Send the combined prompt
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.1)
        )

        return response.text
    except Exception as e:
        return f"API Error: {e}"

# --- DUAL INPUT UI ---
input_method = st.radio(
    "How would you like to provide the contract?",
    ("Upload a File (.txt, .pdf)", "Paste text directly"),
    horizontal=True
)

contract_text = ""

# Handle File Upload (TXT and PDF)
if input_method == "Upload a File (.txt, .pdf)":
    uploaded_file = st.file_uploader(f"Upload Contract (Max {MAX_FILE_SIZE_MB}MB)", type=["txt", "pdf"])

    if uploaded_file is not None:
        # SECURITY CHECK 1: File Size Limit
        if uploaded_file.size > MAX_FILE_SIZE_BYTES:
            st.error(f"🚨 File is too large! Please upload a file smaller than {MAX_FILE_SIZE_MB}MB.")
        else:
            try:
                # Handle PDF
                if uploaded_file.name.endswith(".pdf"):
                    pdf_reader = PyPDF2.PdfReader(uploaded_file)
                    extracted_text = []

                    # SECURITY CHECK 2: Page Limit (Protect API Costs)
                    if len(pdf_reader.pages) > MAX_PDF_PAGES:
                        st.warning(f"Document is very large. Only analyzing the first {MAX_PDF_PAGES} pages to optimize processing.")
                        pages_to_read = MAX_PDF_PAGES
                    else:
                        pages_to_read = len(pdf_reader.pages)

                    for i in range(pages_to_read):
                        page = pdf_reader.pages[i]
                        extracted_text.append(page.extract_text() or "")

                    contract_text = "\n".join(extracted_text)
                    st.success(f"PDF processed! ({pages_to_read} pages read)")

                # Handle Text File
                elif uploaded_file.name.endswith(".txt"):
                    contract_text = uploaded_file.read().decode("utf-8")
                    st.success("Text file processed!")

                with st.expander("View Extracted Raw Text"):
                    st.text(contract_text)

            # SECURITY CHECK 3: Corrupt File Catch
            except Exception as e:
                st.error("🚨 Error reading file. The file may be corrupt, password-protected, or not a valid document.")

# Handle Direct Text Paste
else:
    contract_text = st.text_area("Paste the contract text here:", height=250, placeholder="Paste your legal clauses here...")

# --- EXECUTION ---
if contract_text.strip():
    st.divider()
    if st.button("Generate Legal Summary", type="primary", use_container_width=True):
        with st.spinner("Analyzing legal clauses..."):
            summary = summarize_contract(contract_text)

        st.success("Analysis Complete!")
        st.subheader("Extracted Terms")
        st.info(summary)