from flask import Flask, render_template, request, send_file
import os
from werkzeug.utils import secure_filename
from pdf2docx import Converter
from PIL import Image
import img2pdf
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
import mimetypes

# Inicializar o Flask
app = Flask(__name__)

# Configurações usando variáveis de ambiente
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')  # Pasta padrão: 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Criar pasta de uploads se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Verifica se o arquivo tem uma extensão permitida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Rota principal
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
            if operation == 'jpeg-to-pdf':
                output_path = jpeg_to_pdf(file_paths)
            elif operation == 'pdf-to-word':
                output_path = pdf_to_word(file_paths[0])
            elif operation == 'merge-pdfs':
                output_path = merge_pdfs(file_paths)
            elif operation == 'compress-file':
                output_path = compress_file(file_paths[0])
            else:
                return "Erro: Operação não suportada."

            if not os.path.exists(output_path):
                return "Erro: O arquivo de saída não foi gerado."

            mimetype, _ = mimetypes.guess_type(output_path)
            return send_file(output_path, as_attachment=True, mimetype=mimetype)

        except Exception as e:
            return f"Erro durante o processamento: {str(e)}"

    return render_template('index.html')

# Converter imagens JPEG/PNG para PDF
def jpeg_to_pdf(image_paths):
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'output.pdf')
    with open(output_path, "wb") as f:
        f.write(img2pdf.convert(image_paths))
    return output_path

# Converter PDF para Word (DOCX)
def pdf_to_word(pdf_path):
    docx_path = os.path.splitext(pdf_path)[0] + '.docx'
    cv = Converter(pdf_path)
    cv.convert(docx_path, start=0, end=None)
    cv.close()
    return docx_path

# Mesclar múltiplos arquivos PDF
def merge_pdfs(pdf_paths):
    merger = PdfMerger()
    for pdf in pdf_paths:
        merger.append(pdf)
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'merged.pdf')
    merger.write(output_path)
    merger.close()
    return output_path

# Comprimir PDF ou imagem
def compress_file(file_path):
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

# Iniciar servidor
if __name__ == '__main__':
    debug_mode = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
    app.run(debug=debug_mode)
