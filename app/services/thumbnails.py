import io
import base64
from pathlib import Path
from PIL import Image
import av


def generate_image_thumbnail(file_bytes: bytes, max_size=(120, 120)) -> str:
    """Генерирует Base64 превью для изображений."""
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.thumbnail(max_size)

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=70)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"Ошибка генерации превью изображения: {e}")
        return ""


def generate_video_thumbnail(file_bytes: bytes, max_size=(120, 120)) -> str:
    """Открывает видео прямо из байтовой строки в памяти и делает Base64 превью первого кадра."""
    container = None
    try:
        # Оборачиваем байты в BytesIO
        file_buffer = io.BytesIO(file_bytes)

        # Заставляем PyAV читать прямо из буфера памяти
        container = av.open(file_buffer)
        video_stream = container.streams.video[0]

        for frame in container.decode(video_stream):
            img = frame.to_image()
            img.thumbnail(max_size)

            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=70)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')

    except Exception as e:
        print(f"Ошибка генерации превью видео в памяти: {e}")
    finally:
        if container:
            container.close()
    return ""