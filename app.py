from flask import Flask, render_template, request, send_file
from pathlib import Path
from PIL import Image
import zipfile
import io
import os

app = Flask(__name__)

ALLOWED_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")


def zip_to_pdf_bytes(file_storage) -> io.BytesIO:
    with zipfile.ZipFile(file_storage.stream) as zf:
        infos = [
            info for info in zf.infolist()
            if info.filename.lower().endswith(ALLOWED_EXTS)
        ]

        if not infos:
            raise ValueError("ZIPの中に画像ファイルが見つかりません。")

        infos.sort(key=lambda info: info.date_time)

        images = []
        for info in infos:
            with zf.open(info) as img_file:
                img = Image.open(img_file)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                images.append(img.copy())
                img.close()

        pdf_buffer = io.BytesIO()
        first, *rest = images
        first.save(pdf_buffer, format="PDF", save_all=True, append_images=rest)
        pdf_buffer.seek(0)
        return pdf_buffer


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get("zip_file")
        if not file or file.filename == "":
            return render_template("index.html", error="ZIPファイルを選んでください。")

        try:
            pdf_buffer = zip_to_pdf_bytes(file)
        except ValueError as e:
            return render_template("index.html", error=str(e))
        except Exception:
            return render_template("index.html", error="変換中にエラーが発生しました。")

        stem = Path(file.filename).stem
        download_name = f"{stem}.pdf"

        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=download_name,
        )

    return render_template("index.html", error=None)


if __name__ == "__main__":
    # ローカル開発用（本番は gunicorn 経由）
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
