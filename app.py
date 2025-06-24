from flask import Flask, render_template, request, send_file
import os
import tempfile
from werkzeug.utils import secure_filename
from pdf2docx import Converter
from PyPDF2 import PdfReader, PdfMerger, PdfWriter

app = Flask(__name__)
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_PAGES = 10

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'jpg', 'jpeg', 'png'}

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        operation = request.form.get('operation')
        files = request.files.getlist('files')

        if not files or not operation:
            return "Erro: Nenhum arquivo ou operação selecionada.", 400

        try:
            with tempfile.TemporaryDirectory() as tempdir:
                file_paths = []
                for file in files:
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(tempdir, filename)
                        file.save(file_path)
                        file_paths.append(file_path)

                if not file_paths:
                    return "Erro: Nenhum arquivo válido foi enviado.", 400

                start_page = 0
                end_page = None
                output_path = None

                if operation == 'pdf-to-word':
                    pages_input = request.form.get('pages')
                    if pages_input:
                        try:
                            start, end = map(int, pages_input.split('-'))
                            start_page = start
                            end_page = end
                        except ValueError:
                            return "Formato inválido para páginas. Use ex: 0-5", 400
                    reader = PdfReader(file_paths[0])
                    total_pages = len(reader.pages)
                    if total_pages > MAX_PAGES:
                        return f"Limite de {MAX_PAGES} páginas excedido.", 400
                    output_path = pdf_to_word(file_paths[0], start=start_page, end=end_page, output_dir=tempdir)

                elif operation == 'jpeg-to-pdf':
                    output_path = jpeg_to_pdf(file_paths, output_dir=tempdir)

                elif operation == 'merge-pdfs':
                    output_path = merge_pdfs(file_paths, output_dir=tempdir)

                elif operation == 'compress-file':
                    output_path = compress_file(file_paths[0], output_dir=tempdir)

                elif operation == 'pdf-to-excel':
                    output_path = pdf_to_excel(file_paths[0], output_dir=tempdir)

                else:
                    return "Erro: Operação não suportada.", 400

                if not output_path or not os.path.exists(output_path):
                    return "Erro: O arquivo de saída não foi gerado.", 400

                mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' if output_path.endswith('.docx') else 'application/pdf'
                download_name = os.path.basename(output_path)

                return send_file(
                    output_path,
                    as_attachment=True,
                    mimetype=mimetype,
                    download_name=download_name
                )

        except Exception as e:
            return f"Erro durante o processamento: {str(e)}", 400

    return render_template('index.html')


# Função: JPEG/PNG ➜ PDF
def jpeg_to_pdf(image_paths, output_dir=None):
    from PIL import Image
    output_path = os.path.join(output_dir, 'output.pdf')
    images = [Image.open(img).convert('RGB') for img in image_paths]
    images[0].save(output_path, save_all=True, append_images=images[1:])
    return output_path


# Função: PDF ➜ Word (.docx)
def pdf_to_word(pdf_path, start=0, end=None, output_dir=None):
    docx_path = os.path.join(output_dir, os.path.splitext(os.path.basename(pdf_path))[0] + '.docx')
    cv = Converter(pdf_path)
    cv.convert(docx_path, start=start, end=end)
    cv.close()
    return docx_path


# Função: Unir múltiplos PDFs
def merge_pdfs(pdf_paths, output_dir=None):
    merger = PdfMerger()
    for pdf in pdf_paths:
        merger.append(pdf)
    output_path = os.path.join(output_dir, 'merged.pdf')
    merger.write(output_path)
    merger.close()
    return output_path


# Função: Comprimir PDF ou imagem
def compress_file(file_path, output_dir=None):
    from PIL import Image
    ext = os.path.splitext(file_path)[1].lower()
    compressed_path = os.path.join(output_dir, 'compressed_' + os.path.basename(file_path))
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


# Nova função: PDF ➜ Excel (.xlsx)
def pdf_to_excel(pdf_path, output_dir=None):
    import camelot
    import pandas as pd

    tables = camelot.read_pdf(pdf_path, pages='all')

    if not tables:
        raise ValueError("Nenhuma tabela encontrada no PDF.")

    output_path = os.path.join(output_dir, 'output.xlsx')

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for i, table in enumerate(tables):
            sheet_name = f'Table_{i+1}'
            table.df.to_excel(writer, sheet_name=sheet_name[:31], index=False)  # Máximo 31 caracteres

    return output_path


if __name__ == '__main__':
    app.run(debug=False)
