from flask import Flask, render_template, request, send_file, after_this_request
import os
from werkzeug.utils import secure_filename
from pdf2docx import Converter
from PIL import Image
import img2pdf
from PyPDF2 import PdfMerger, PdfReader, PdfWriter

# Inicializar o Flask
app = Flask(__name__)

# Configurações com variáveis de ambiente
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024  # Limite: 30 MB

# Criar pasta de uploads se necessário
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Verificação de extensão permitida
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

        # Processar operação solicitada
        if operation == 'jpeg-to-pdf':
            output_path = jpeg_to_pdf(file_paths)
        elif operation == 'pdf-to-word':
            output_path = pdf_to_word(file_paths[0])
            if not output_path:
                return "Erro ao converter PDF para Word. Verifique o arquivo."
        elif operation == 'merge-pdfs':
            output_path = merge_pdfs(file_paths)
        elif operation == 'compress-file':
            output_path = compress_file(file_paths[0])
            if not output_path:
                return "Erro: Tipo de arquivo não suportado para compressão."
        else:
            return "Erro: Operação não suportada."

        @after_this_request
        def cleanup(response):
            try:
                # Excluir arquivos de entrada e saída
                for path in file_paths:
                    if os.path.exists(path):
                        os.remove(path)
                if os.path.exists(output_path):
                    os.remove(output_path)
            except Exception as e:
                print(f"Erro ao excluir arquivos temporários: {e}")
            return response

        return send_file(output_path, as_attachment=True)

    return render_template('index.html')

# Conversão JPEG para PDF
def jpeg_to_pdf(image_paths):
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'output.pdf')
    with open(output_path, "wb") as f:
        f.write(img2pdf.convert([str(p) for p in image_paths]))
    return output_path

# Conversão PDF para Word com tratamento e limite de páginas
def pdf_to_word(pdf_path, max_pages=20):
    docx_path = os.path.splitext(pdf_path)[0] + '.docx'
    try:
        total_pages = len(PdfReader(pdf_path).pages)
        end_page = min(max_pages, total_pages)
        with Converter(pdf_path) as cv:
            cv.convert(docx_path, start=0, end=end_page)
        return docx_path
    except Exception as e:
        print(f"Erro na conversão PDF → Word: {e}")
        return None

# Mesclar múltiplos PDFs
def merge_pdfs(pdf_paths):
    merger = PdfMerger()
    for pdf in pdf_paths:
        merger.append(pdf)
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'merged.pdf')
    merger.write(output_path)
    merger.close()
    return output_path

# Compressão de PDF ou imagem
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
        try:
            img = Image.open(file_path)
            img.save(compressed_path, optimize=True, quality=40)
        except Exception as e:
            print(f"Erro ao comprimir imagem: {e}")
            return None
    else:
        return None

    return compressed_path

# Executar o servidor
if __name__ == '__main__':
    debug_mode = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
    app.run(debug=debug_mode)
