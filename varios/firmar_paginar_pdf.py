"""Anota cada pagina de un PDF con un cuadro numerado y una imagen debajo.

Uso:
    python firmar_paginar_pdf.py \
        --input archivo.pdf \
        --output archivo_salida.pdf \
        --image firma.png

Por defecto, el cuadro se coloca en la esquina superior derecha.
Si necesitas anclarlo al borde izquierdo, usa: --edge left
"""

from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def _overlay_page(
    page_width: float,
    page_height: float,
    page_number: int,
    image_path: Path | None,
    edge: str,
    box_size: float,
    border_width: float,
    page_margin: float,
    gap: float,
    image_max_width: float,
) -> BytesIO:
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))

    if edge == "right":
        box_x = page_width - box_size - page_margin
    else:
        box_x = page_margin

    box_y = page_height - box_size - page_margin

    c.setLineWidth(border_width)
    c.setStrokeColorRGB(0, 0, 0)
    c.rect(box_x, box_y, box_size, box_size, stroke=1, fill=0)

    font_size = max(9, box_size * 0.42)
    c.setFont("Helvetica-Bold", font_size)
    c.drawCentredString(
        box_x + (box_size / 2),
        box_y + (box_size - font_size) / 2 + 2,
        str(page_number),
    )


    # Solo dibuja la imagen si se proporciona image_path
    if image_path is not None:
        img_reader = ImageReader(str(image_path))
        img_w, img_h = img_reader.getSize()
        scale = image_max_width / float(img_w)
        draw_w = image_max_width
        draw_h = float(img_h) * scale

        if edge == "right":
            img_x = box_x + box_size - draw_w
        else:
            img_x = box_x
        img_y = box_y - gap - draw_h

        if img_y < 0:
            img_y = 0

        c.drawImage(
            img_reader,
            img_x,
            img_y,
            width=draw_w,
            height=draw_h,
            mask="auto",
            preserveAspectRatio=True,
            anchor="sw",
        )

    c.save()
    packet.seek(0)
    return packet


def anotar_pdf(
    input_pdf: Path,
    output_pdf: Path,
    image_path: Path | None = None,
    edge: str = "right",
    box_size: float = 30,
    border_width: float = 1,
    page_margin: float = 0,
    gap: float = 4,
    image_max_width: float | None = None,
) -> None:
    reader = PdfReader(str(input_pdf))
    writer = PdfWriter()

    final_image_width = image_max_width if image_max_width is not None else (box_size * 2)

    for idx, page in enumerate(reader.pages, start=1):
        # Primero normaliza rotaciones internas para trabajar en coordenadas reales.
        if page.get("/Rotate", 0):
            page.transfer_rotation_to_content()

        # Asegura orientacion vertical antes de firmar: si esta horizontal,
        # la gira y vuelve a fijar la rotacion en el contenido.
        if float(page.mediabox.width) > float(page.mediabox.height):
            page.rotate(90)
            page.transfer_rotation_to_content()

        width = float(page.mediabox.width)
        height = float(page.mediabox.height)

        overlay_stream = _overlay_page(
            page_width=width,
            page_height=height,
            page_number=idx,
            image_path=image_path,
            edge=edge,
            box_size=box_size,
            border_width=border_width,
            page_margin=page_margin,
            gap=gap,
            image_max_width=final_image_width,
        )

        overlay_pdf = PdfReader(overlay_stream)
        page.merge_page(overlay_pdf.pages[0])
        writer.add_page(page)

    with output_pdf.open("wb") as f_out:
        writer.write(f_out)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Agrega en cada pagina un cuadro con numero y una imagen justo debajo (opcional)."
        )
    )
    parser.add_argument("--input", required=True, type=Path, help="Ruta del PDF de entrada")
    parser.add_argument("--output", required=True, type=Path, help="Ruta del PDF de salida")
    parser.add_argument("--image", required=False, type=Path, help="Ruta de la imagen (firma, opcional)")
    parser.add_argument(
        "--edge",
        choices=["left", "right"],
        default="right",
        help="Borde al que se ancla el cuadro y la imagen (default: right)",
    )
    parser.add_argument(
        "--box-size",
        type=float,
        default=30,
        help="Tamano del cuadro numerado en puntos (default: 30)",
    )
    parser.add_argument(
        "--border-width",
        type=float,
        default=1,
        help="Grosor del borde del cuadro (default: 1)",
    )
    parser.add_argument(
        "--margin",
        type=float,
        default=0,
        help="Margen al borde de pagina (default: 0)",
    )
    parser.add_argument(
        "--gap",
        type=float,
        default=4,
        help="Separacion entre cuadro e imagen (default: 4)",
    )
    parser.add_argument(
        "--image-width",
        type=float,
        default=None,
        help="Ancho maximo de la imagen en puntos (default: 2 x box-size)",
    )
    return parser.parse_args()



def main() -> None:
    args = parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"No existe el PDF de entrada: {args.input}")
    image_path = args.image if args.image is not None else None
    if image_path is not None and not image_path.exists():
        raise FileNotFoundError(f"No existe la imagen: {image_path}")

    anotar_pdf(
        input_pdf=args.input,
        output_pdf=args.output,
        image_path=image_path,
        edge=args.edge,
        box_size=args.box_size,
        border_width=args.border_width,
        page_margin=args.margin,
        gap=args.gap,
        image_max_width=args.image_width,
    )

    print(f"PDF generado: {args.output}")


if __name__ == "__main__":
    main()
