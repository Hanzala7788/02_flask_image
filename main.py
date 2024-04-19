import os
from io import BytesIO
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
from PIL import Image

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'avif'}


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'
db = SQLAlchemy(app)

app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['Download_FOLDER'] = 'static/downloads'

class Upload(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	filename = db.Column(db.String(50))
	data = db.Column(db.LargeBinary)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ProcessImages(filename, operation):
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(upload_path):
        flash(f"File {filename} not found in the upload folder.")
        return

    img = Image.open(upload_path)
    img_format = img.format

    if operation == 'grayscale':
        img = img.convert('L')
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        new_upload = Upload(filename=f"grayscale_{filename}", data=img_bytes.getvalue())
        db.session.add(new_upload)
        db.session.commit()
    elif operation in {'png', 'jpg', 'webp', 'avif'}:
        if operation == 'png':
            if img_format == 'PNG':
                # Save the original PNG file without any conversion
                img_bytes = BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                new_upload = Upload(filename=filename, data=img_bytes.getvalue())
                db.session.add(new_upload)
                db.session.commit()
            else:
                # Convert the image to PNG format
                img_bytes = BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                new_filename = f"{filename.split('.')[0]}.png"
                new_upload = Upload(filename=new_filename, data=img_bytes.getvalue())
                db.session.add(new_upload)
                db.session.commit()
        elif operation == 'jpg':
            output_format = 'JPEG'
            extension = 'jpg'
            # Convert RGBA to RGB if necessary
            if img.mode == 'RGBA':
                img = img.convert('RGB')
        # ... (rest of the code for other operations)
    else:
        # Save the file with its original format
        img_bytes = BytesIO()
        img.save(img_bytes, format=img.format)
        img_bytes.seek(0)
        new_upload = Upload(filename=filename, data=img_bytes.getvalue())
        db.session.add(new_upload)
        db.session.commit()

@app.route('/')
@app.route('/home', methods=['GET', 'POST'])
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/edit', methods=['GET', 'POST'])
def edit():
    if request.method == 'POST':
        file = request.files['file']
        if not file:
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            ProcessImages(filename, request.form['operation'])
            uploads = Upload.query.filter(Upload.filename.like(f"%{filename}%")).all()
            return render_template('edit.html', uploads=uploads)
        else:
            flash('File type not allowed')
            return redirect(request.url)
    else:
        uploads = Upload.query.all()
        return render_template('edit.html', uploads=uploads)

@app.route('/download/<upload_id>')
def download(upload_id):
    upload = Upload.query.filter_by(id=upload_id).first()
    if upload:
        return send_file(BytesIO(upload.data), download_name=upload.filename, as_attachment=True)
    else:
        flash('File not found')
        return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
