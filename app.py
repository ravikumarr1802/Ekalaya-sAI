import streamlit as st
import os
import csv
from dotenv import load_dotenv
import google.generativeai as genai
from PyPDF2 import PdfReader
from io import BytesIO
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-pro")
chat = model.start_chat(history=[])

def get_gemini_response(question):
    response = chat.send_message(question, stream=True)
    return response

def read_pdf(file):
    pdf_reader = PdfReader(file)
    text = ""
    for page_num in range(len(pdf_reader.pages)):
        text += pdf_reader.pages[page_num].extract_text()
    return text

def predict_questions(syllabus, paper1, paper2):
    prompt = f"Based on this syllabus: {syllabus}, and the past papers: {paper1}, {paper2}, predict potential exam questions."
    response = get_gemini_response(prompt)
    response_text = ""
    for chunk in response:
        response_text += chunk.text
    return response_text

def generate_csv(predicted_text):
    output = io.StringIO()
    csv_writer = csv.writer(output)
    csv_writer.writerow(["Unit", "Generated Questions"])

    units = predicted_text.split("Unit")
    for i, unit_text in enumerate(units[1:], start=1):
        questions = unit_text.strip().splitlines()
        for question in questions:
            csv_writer.writerow([f"Unit {i}", question.strip()])

    output.seek(0)
    return output.getvalue().encode('utf-8')

def generate_pdf(predicted_text):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    text_object = c.beginText(40, height - 40)
    text_object.setFont("Helvetica", 12)
    text_object.setLeading(14)

    for i, unit_questions in enumerate(predicted_text.split("Unit"), start=1):
        text_object.textLine(f"Unit {i}:")
        for line in unit_questions.strip().splitlines():
            text_object.textLine(line)
        text_object.textLine("\n")

    c.drawText(text_object)
    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer

st.set_page_config(page_title="Question Paper Generation", layout="wide")

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("styles.css")

st.header("Question Paper Generator")

syllabus_file = st.file_uploader("Upload Syllabus PDF", type=["pdf"], key="syllabus")
previous_paper1 = st.file_uploader("Upload Previous Year Question Paper 1", type=["pdf"], key="paper1")
previous_paper2 = st.file_uploader("Upload Previous Year Question Paper 2", type=["pdf"], key="paper2")

if st.button("Predict Questions") and syllabus_file and previous_paper1 and previous_paper2:
    syllabus_text = read_pdf(syllabus_file)
    paper1_text = read_pdf(previous_paper1)
    paper2_text = read_pdf(previous_paper2)

    predicted_questions = predict_questions(syllabus_text, paper1_text, paper2_text)

    st.subheader("Generated Questions:")
    st.markdown(f'<div class="response">{predicted_questions}</div>', unsafe_allow_html=True)

    csv_data = generate_csv(predicted_questions)
    st.download_button(label="Download Generated Questions CSV", 
                       data=csv_data, 
                       file_name="generated_questions.csv", 
                       mime="text/csv")

    pdf_data = generate_pdf(predicted_questions)
    st.download_button(label="Download Generated Questions PDF", 
                       data=pdf_data, 
                       file_name="generated_questions.pdf",
                       mime="application/pdf")

else:
    st.warning("Please upload all files to predict questions.")
