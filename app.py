from flask import Flask, render_template, request, send_file
import os
from werkzeug.utils import secure_filename
from pdf2docx import Converter
from PIL import Image
import img2pdf
from PyPDF2 import PdfMerger, PdfReader, PdfWriter

# Inicializar o Flask
app = Flask(__name__)

# Configurações usando variáveis de ambiente
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')  # Pasta de uploads (padrão: 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Criar a pasta de uploads se ela não existir
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Função para verificar extensões permitidas
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

        # Salvar arquivos temporariamente
        file_paths = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                file_paths.append(file_path)

        # Realizar a operação selecionada
        if operation == 'jpeg-to-pdf':
            output_path = jpeg_to_pdf(file_paths)
        elif operation == 'pdf-to-word':
            output_path = pdf_to_word(file_paths[0])
        elif operation == 'merge-pdfs':
            output_path = merge_pdfs(file_paths)
        elif operation == 'compress-file':
            output_path = compress_file(file_paths[0])
        else:
            return "Operação não suportada."

        # Retornar o arquivo gerado para download
        return send_file(output_path, as_attachment=True)

    return render_template('index.html')

# Funções de processamento de arquivos
def jpeg_to_pdf(image_paths):
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'output.pdf')
    with open(pdf_path, "wb") as f:
        f.write(img2pdf.convert([str(path) for path in image_paths]))
    return pdf_path

def pdf_to_word(pdf_path):
    docx_path = os.path.splitext(pdf_path)[0] + '.docx'
    cv = Converter(pdf_path)
    cv.convert(docx_path, start=0, end=None)
    cv.close()
    return docx_path

def merge_pdfs(pdf_paths):
    merger = PdfMerger()
    for pdf in pdf_paths:
        merger.append(pdf)
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'merged.pdf')
    merger.write(output_path)
    merger.close()
    return output_path

def compress_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    compressed_path = os.path.join(app.config['UPLOAD_FOLDER'], 'compressed_' + os.path.basename(file_path))

    if ext == '.pdf':
        # Comprimir PDF
        reader = PdfReader(file_path)
        writer = PdfWriter()
        for page in reader.pages:
            page.compress_content_streams()  # Comprime o conteúdo da página
            writer.add_page(page)
        with open(compressed_path, 'wb') as f:
            writer.write(f)

    elif ext in ['.jpg', '.jpeg', '.png']:
        # Comprimir imagem com uma qualidade fixa (sem loop de ajuste)
        img = Image.open(file_path)
        img.save(compressed_path, optimize=True, quality=40)  # Qualidade fixa para garantir compressão significativa

    else:
        return None  # Formato não suportado

    return compressed_path

# Executar o servidor
if __name__ == '__main__':
    app.run(debug=os.getenv('DEBUG_MODE', 'False').lower() == 'true')  # Modo de depuração via variável de ambiente
