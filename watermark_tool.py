import os
import argparse
from PIL import Image, ImageDraw, ImageFont, ExifTags
from datetime import datetime
import shutil


def get_exif_date(image_path):
    """
    从图片EXIF信息中提取拍摄日期。
    """
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()

        if exif_data:
            for tag, value in exif_data.items():
                tag_name = ExifTags.TAGS.get(tag, tag)
                if tag_name == 'DateTimeOriginal' or tag_name == 'DateTime':
                    # EXIF日期格式通常是 "YYYY:MM:DD HH:MM:SS"
                    # 我们只需要 "YYYY-MM-DD"
                    date_str = value.split(' ')[0].replace(':', '-')
                    return date_str
        return None
    except Exception as e:
        print(f"无法读取 {image_path} 的EXIF信息或日期：{e}")
        return None


def add_watermark(image_path, watermark_text, font_size, font_color, position):
    """
    在图片上添加文本水印。
    """
    try:
        img = Image.open(image_path).convert("RGBA")  # 转换为RGBA以支持透明度和颜色
        draw = ImageDraw.Draw(img)

        # 尝试加载一个默认字体，如果用户没有指定或系统没有，则使用Pillow内置的默认字体
        try:
            # 常见系统字体路径，你可能需要根据操作系统调整
            # macOS: /Library/Fonts/Arial.ttf
            # Windows: C:/Windows/Fonts/arial.ttf
            # Linux: /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
            font_path = "arial.ttf"  # 尝试使用Arial，如果不存在，Pillow会fallback
            font = ImageFont.truetype(font_path, font_size)
        except IOError:
            print(f"警告：无法找到 {font_path} 字体，使用Pillow默认字体。")
            font = ImageFont.load_default()  # Load default font if specified font not found
            # 调整默认字体的大小，因为load_default()不支持直接设置大小
            # 如果使用load_default()，字体大小可能不会按预期工作，需要更复杂的逻辑来模拟
            # 对于简单的文本，load_default()通常足够
            # 这里我们不作进一步处理，保留font_size作为参数，但load_default()会忽略它

        # 获取文本的边界框（left, top, right, bottom）
        # draw.textbbox 是 Pillow 9.2.0+ 的推荐方法
        try:
            text_bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
        except AttributeError:
            # 对于旧版Pillow，使用 textsize
            text_width, text_height = draw.textsize(watermark_text, font=font)

        img_width, img_height = img.size

        # 计算水印位置
        if position == 'top-left':
            x, y = 10, 10
        elif position == 'center':
            x = (img_width - text_width) / 2
            y = (img_height - text_height) / 2
        elif position == 'bottom-right':
            x = img_width - text_width - 10
            y = img_height - text_height - 10
        else:  # 默认为左上角
            x, y = 10, 10

        # 将颜色字符串转换为 (R, G, B) 或 (R, G, B, A) 元组
        # Pillow的颜色解析器支持多种格式，如"red", "#FF0000"等
        # 如果需要透明度，可以在这里处理

        draw.text((x, y), watermark_text, fill=font_color, font=font)

        return img
    except Exception as e:
        print(f"在图片 {image_path} 上添加水印失败：{e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="为图片文件添加EXIF拍摄日期水印。")
    parser.add_argument("input_path", type=str,
                        help="包含图片文件的目录路径。")
    parser.add_argument("--font_size", type=int, default=30,
                        help="水印字体大小 (默认: 30)。")
    parser.add_argument("--font_color", type=str, default="white",
                        help="水印字体颜色 (例如: 'white', 'red', '#RRGGBB', 默认: 'white')。")
    parser.add_argument("--position", type=str, default="bottom-right",
                        choices=['top-left', 'center', 'bottom-right'],
                        help="水印在图片上的位置 (默认: 'bottom-right')。")

    args = parser.parse_args()

    input_dir = args.input_path

    if not os.path.isdir(input_dir):
        print(f"错误：输入的路径 '{input_dir}' 不是一个有效的目录。")
        return

    output_dir_name = os.path.basename(input_dir) + "_watermark"
    output_dir = os.path.join(input_dir, output_dir_name)  # 作为原目录的子目录

    # 如果输出目录已存在，先删除再创建，确保干净
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    print(f"水印图片将保存到：{output_dir}")

    supported_extensions = ('.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif')  # 支持的图片格式

    processed_count = 0
    for root, _, files in os.walk(input_dir):
        # 排除已经创建的_watermark子目录，避免无限循环处理
        if output_dir in root:
            continue

        for filename in files:
            if filename.lower().endswith(supported_extensions):
                image_path = os.path.join(root, filename)
                print(f"正在处理：{image_path}")

                watermark_text = get_exif_date(image_path)
                if watermark_text is None:
                    watermark_text = "日期缺失"  # 如果没有EXIF日期，使用默认文本
                    print(f"警告：'{filename}' 未找到EXIF拍摄日期，使用默认文本：'{watermark_text}'。")

                watermarked_img = add_watermark(
                    image_path,
                    watermark_text,
                    args.font_size,
                    args.font_color,
                    args.position
                )

                if watermarked_img:
                    # 构建新的文件名，例如 original_image_watermarked.jpg
                    base_name, ext = os.path.splitext(filename)
                    output_filename = f"{base_name}_watermarked{ext}"

                    # 确保相对路径在输出目录中保持
                    relative_path = os.path.relpath(root, input_dir)
                    current_output_subdir = os.path.join(output_dir, relative_path)
                    os.makedirs(current_output_subdir, exist_ok=True)

                    output_image_path = os.path.join(current_output_subdir, output_filename)

                    # 对于JPG图像，保存时可能需要转换为RGB模式，因为RGBA在某些情况下不被JPG支持
                    if ext.lower() in ('.jpg', '.jpeg'):
                        watermarked_img = watermarked_img.convert("RGB")

                    watermarked_img.save(output_image_path)
                    print(f"已保存：{output_image_path}")
                    processed_count += 1
                else:
                    print(f"跳过 '{filename}'，因为添加水印失败。")

    print(f"\n处理完成。共处理了 {processed_count} 张图片。")
    print(f"所有带水印的图片已保存到 '{output_dir}' 目录下。")


if __name__ == "__main__":
    main()