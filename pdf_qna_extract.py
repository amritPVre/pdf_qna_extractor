# -*- coding: utf-8 -*-
"""
Created on Wed Sep  3 19:03:14 2025

@author: amrit
"""

import streamlit as st
import pdfplumber
import pandas as pd
import io
from openai import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
import json

# ------------------------------
# CONFIGURE OPENROUTER CLIENT
# ------------------------------
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=st.secrets["OPENROUTER_API_KEY"],  # store in Streamlit secrets
)

# ------------------------------
# PAGE CONFIG
# ------------------------------
st.set_page_config(page_title="AI-Powered QnA Extractor", page_icon="📘", layout="centered")

# ------------------------------
# CUSTOM STYLES
# ------------------------------
st.markdown(
    """
    <style>
    .main { background-color: #F9FAFB; }
    .stApp { background-color: #ffffff; }
    h1, h2, h3 { color: #0F4C81; font-family: 'Helvetica Neue', sans-serif; }
    .css-1d391kg p { font-size: 16px; line-height: 1.6; }
    .stDownloadButton button {
        background-color: #0F4C81;
        color: white;
        font-weight: bold;
        border-radius: 10px;
        padding: 0.6em 1.2em;
    }
    .stDownloadButton button:hover {
        background-color: #145DA0;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ------------------------------
# APP TITLE + DESCRIPTION
# ------------------------------
st.title("📘 AI-Agentic QnA Extractor")
st.subheader(" - Handles 200+ Pages at Once")
st.markdown(
    """
    Welcome to the **QnA Extractor App**! 🎯  
    This tool helps you upload a **QnA-style PDF (interview prep, study guide, exam book, etc.)**,  
    then uses **AI Agent** to extract **Questions & Answers** into a clean Excel file.  

    ### 📖 How to Use:
    1. **Upload your QnA PDF** file.  
    2. The app will process text in **chunks using Latest Industry Tech** to handle large files.  
    3. AI will extract structured **Question–Answer pairs**.  
    4. Preview results and **download as Excel**.  

    ⚡ *Tip: The AI runs only once per PDF upload. Downloading won’t cost extra API calls!*  
    """
)

# ------------------------------
# SESSION STATE INIT
# ------------------------------
if "qna_list" not in st.session_state:
    st.session_state.qna_list = None
if "excel_file" not in st.session_state:
    st.session_state.excel_file = None

# ------------------------------
# FILE UPLOAD
# ------------------------------
uploaded_file = st.file_uploader("📂 Upload your QnA PDF", type=["pdf"])

if uploaded_file is not None:
    if st.session_state.qna_list is None:  # run AI only first time
        with st.spinner("⏳ Extracting text from PDF and sending to AI..."):
            # STEP 1: Extract text
            text = ""
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

            # STEP 2: Split into chunks
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1500,
                chunk_overlap=200,
            )
            chunks = splitter.split_text(text)

            st.info(f"🔹 PDF successfully split into **{len(chunks)} chunks** for AI processing.")

            qna_list = []

            # STEP 3: AI extraction
            for idx, chunk in enumerate(chunks, 1):
                with st.spinner(f"🤖 Processing chunk {idx}/{len(chunks)}..."):
                    prompt = f"""
                    You are an assistant that extracts QnA pairs from text.
                    Given the following chunk, return QnA pairs in strict JSON format as a list of objects:

                    Example:
                    [
                      {{ "question": "What is solar PV?", "answer": "Solar PV is ..." }},
                      {{ "question": "Define irradiance.", "answer": "Irradiance is ..." }}
                    ]

                    Text chunk:
                    {chunk}
                    """

                    completion = client.chat.completions.create(
                        model="deepseek/deepseek-chat-v3.1:free",
                        messages=[
                            {"role": "system", "content": "You extract structured QnA."},
                            {"role": "user", "content": prompt},
                        ],
                        extra_headers={
                            "HTTP-Referer": "https://yourappurl.com",
                            "X-Title": "QnA Extractor App",
                        },
                        temperature=0,
                    )

                    try:
                        result = completion.choices[0].message.content
                        extracted = json.loads(result)
                        qna_list.extend(extracted)
                    except Exception as e:
                        st.error(f"⚠️ Error parsing chunk {idx}: {e}")

            # Save results
            st.session_state.qna_list = qna_list

            if qna_list:
                df = pd.DataFrame(qna_list)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    df.to_excel(writer, index=False, sheet_name="QnA")
                st.session_state.excel_file = output.getvalue()

    # ------------------------------
    # DISPLAY + DOWNLOAD
    # ------------------------------
    if st.session_state.qna_list:
        df = pd.DataFrame(st.session_state.qna_list)
        st.success("✅ Extraction completed! Preview below:")

        st.dataframe(df.head(10), use_container_width=True)

        st.download_button(
            label="📥 Download Full Excel File",
            data=st.session_state.excel_file,
            file_name="QnA_AI_Extracted.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        if st.button("🔄 Clear & Upload Another PDF"):
            st.session_state.qna_list = None
            st.session_state.excel_file = None
            st.experimental_rerun()
