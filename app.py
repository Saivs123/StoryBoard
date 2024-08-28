import os
import requests
import io
import PyPDF2
from fpdf import FPDF
import streamlit as st
from PIL import Image

# Set your Hugging Face API key here
API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev"
headers = {"Authorization": "Bearer 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"}

CHUNK_SIZE = 100  # Number of words per chunk

def query_image_generation(prompt):
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
        if response.status_code == 200:
            return response.content
        else:
            st.error(f"Failed to generate image. Status code: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error while querying image generation: {e}")
        return None

def generate_image(prompt, index, book_name):
    # Create images directory based on book name
    images_dir = os.path.join("images", book_name)
    os.makedirs(images_dir, exist_ok=True)

    image_bytes = query_image_generation(prompt)
    if image_bytes:
        image = Image.open(io.BytesIO(image_bytes))
        image_path = os.path.join(images_dir, f"image_{index}.png")
        image.save(image_path)
        st.success(f"Image saved: {image_path}")
        return image_path
    else:
        st.error(f"Failed to save image for prompt: {prompt}")
        return None

def extract_text_from_pdf(pdf_file):
    try:
        with open(pdf_file, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + " "
        return text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
        return None

def sanitize_text(text):
    return text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")

def divide_into_chunks(text, chunk_size):
    words = text.split()
    return [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

class CustomPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Storybook', 0, 1, 'C')

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def compile_storybook(chunks, images, filename):
    pdf = CustomPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for i, (chunk, image) in enumerate(zip(chunks, images)):
        pdf.add_page()
        pdf.set_font("Arial", 'B', size=16)
        pdf.cell(0, 10, f"Chapter {i+1}", 0, 1, 'C')
        pdf.ln(5)
        pdf.set_font("Arial", size=12)
        try:
            pdf.multi_cell(0, 10, chunk)
        except Exception as e:
            st.error(f"Error adding text to PDF: {e}")
            pdf.multi_cell(0, 10, "Text could not be added due to encoding issues.")
        if image and os.path.exists(image):
            pdf.image(image, x=55, y=pdf.get_y() + 10, w=100)
        else:
            pdf.cell(0, 10, "No image available", 0, 1, 'C')
    
    pdf.output(filename)
    st.success(f"Storybook successfully created as {filename}!")

def main():
    st.title("Storybook Generator")

    pdf_file = st.file_uploader("Upload your PDF", type=["pdf"])
    chunk_size = st.number_input("Chunk size (number of words per chunk)", min_value=10, max_value=500, value=100)
    book_name = st.text_input("Enter book name", "storybook.pdf")

    if st.button("Generate Storybook"):
        if pdf_file and book_name:
            pdf_path = "uploaded.pdf"
            with open(pdf_path, "wb") as f:
                f.write(pdf_file.getbuffer())
            
            text = extract_text_from_pdf(pdf_path)
            if not text:
                st.error("Failed to extract text from PDF.")
                return

            sanitized_text = sanitize_text(text)
            chunks = divide_into_chunks(sanitized_text, chunk_size)
            
            images = []
            for i, chunk in enumerate(chunks):
                image_path = generate_image(chunk, i, book_name)
                images.append(image_path if image_path else None)
            
            try:
                output_filename = f"{book_name}.pdf"
                compile_storybook(chunks, images, output_filename)
                st.download_button("Download Storybook", data=open(output_filename, 'rb'), file_name=output_filename)
            except Exception as e:
                st.error(f"Error during storybook compilation: {e}")

if __name__ == "__main__":
    main()
