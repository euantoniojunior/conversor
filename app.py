from flask import Flask, render_template, request, send_file
import os
from werkzeug.utils import secure_filename
from pdf2docx import Converter
from PyPDF2 import PdfReader

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_PAGES = 10

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf'}

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        operation = request.form.get('operation')
        files = request.files.getlist('files')

        if not files or not operation:
            return "Erro: Nenhum arquivo ou operação selecionada."

        file_paths = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                file_paths.append(file_path)

        if not file_paths:
            return "Erro: Nenhum arquivo válido foi enviado."

        try:
            start_page = 0
            end_page = None

            if operation == 'pdf-to-word':
                pages_input = request.form.get('pages')
                if pages_input:
                    try:
                        start, end = map(int, pages_input.split('-'))
                        start_page = start
                        end_page = end
                    except:
                        return "Formato inválido para páginas. Use ex: 0-5"

                reader = PdfReader(file_paths[0])
                total_pages = len(reader.pages)
                if total_pages > MAX_PAGES:
                    return f"Limite de {MAX_PAGES} páginas excedido."

                output_path = pdf_to_word(file_paths[0], start=start_page, end=end_page)

            elif operation == 'jpeg-to-pdf':
                output_path = jpeg_to_pdf(file_paths)
            elif operation == 'merge-pdfs':
                output_path = merge_pdfs(file_paths)
            elif operation == 'compress-file':
                output_path = compress_file(file_paths[0])
            else:
                return "Erro: Operação não suportada."

            if not os.path.exists(output_path):
                return "Erro: O arquivo de saída não foi gerado."

            mimetype, _ = os.path.splitext(output_path)
            mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' if mimetype == '.docx' else 'application/pdf'

            return send_file(output_path, as_attachment=True, mimetype=mimetype)

        except Exception as e:
            return f"Erro durante o processamento: {str(e)}"

    return render_template('index.html')

# Converter imagens JPEG/PNG para PDF
def jpeg_to_pdf(image_paths):
    from PIL import Image
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'output.pdf')
    images = [Image.open(img).convert('RGB') for img in image_paths]
    images[0].save(output_path, save_all=True, append_images=images[1:])
    return output_path

# Converter PDF para Word (DOCX)
def pdf_to_word(pdf_path, start=0, end=None):
    docx_path = os.path.splitext(pdf_path)[0] + '.docx'
    cv = Converter(pdf_path)
    cv.convert(docx_path, start=start, end=end)
    cv.close()
    return docx_path

# Mesclar múltiplos arquivos PDF
def merge_pdfs(pdf_paths):
    from PyPDF2 import PdfMerger
    merger = PdfMerger()
    for pdf in pdf_paths:
        merger.append(pdf)
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'merged.pdf')
    merger.write(output_path)
    merger.close()
    return output_path

# Comprimir PDF ou imagem
def compress_file(file_path):
    from PIL import Image
    from PyPDF2 import PdfReader, PdfWriter

    ext = os.path.splitext(file_path)[1].lower()
    compressed_path = os.path.join(app.config['UPLOAD_FOLDER'], 'compressed_' + os.path.basename(file_path))

    if ext == '.pdf':
        reader = PdfReader(file_path)
        writer = PdfWriter()
        for page in reader.pages:
            page.compress_content_streams()
            writer.add_page(page)
        with open(compressed_path, 'wb') as f:
            writer.write(f)

    elif ext in ['.jpg', '.jpeg', '.png']:
        img = Image.open(file_path)
        img.save(compressed_path, optimize=True, quality=40)

    else:
        return None

    return compressed_path

if __name__ == '__main__':
    app.run(debug=False)
