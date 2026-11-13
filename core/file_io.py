"""Чтение и запись текстовых файлов в UTF-8."""

READ_ENCODING = "utf-8-sig"  # BOM при чтении отбрасывается
WRITE_ENCODING = "utf-8"


class FileOperationError(Exception):
    """Ошибка чтения/записи; текст сообщения показывается пользователю."""


def read_text_file(path: str) -> str:
    """CRLF и CR приводятся к \\n."""
    try:
        with open(path, "r", encoding=READ_ENCODING) as file:
            return file.read()
    except FileNotFoundError:
        raise FileOperationError(f"Файл не найден:\n{path}") from None
    except IsADirectoryError:
        raise FileOperationError(f"Указанный путь является папкой, а не файлом:\n{path}") from None
    except PermissionError:
        raise FileOperationError(f"Недостаточно прав для чтения файла:\n{path}") from None
    except UnicodeDecodeError:
        raise FileOperationError(
            f"Не удалось прочитать файл:\n{path}\n\n"
            "Файл не является текстовым файлом в кодировке UTF-8."
        ) from None
    except OSError as error:
        raise FileOperationError(_describe_os_error("Не удалось открыть файл", path, error)) from None


def write_text_file(path: str, text: str) -> None:
    """Окончания строк — LF."""
    try:
        with open(path, "w", encoding=WRITE_ENCODING, newline="\n") as file:
            file.write(text)
    except IsADirectoryError:
        raise FileOperationError(f"Указанный путь является папкой, а не файлом:\n{path}") from None
    except PermissionError:
        raise FileOperationError(f"Недостаточно прав для записи в файл:\n{path}") from None
    except UnicodeEncodeError:
        raise FileOperationError(
            f"Не удалось сохранить файл:\n{path}\n\n"
            "Текст содержит символы, которые нельзя записать в UTF-8."
        ) from None
    except OSError as error:
        raise FileOperationError(_describe_os_error("Не удалось сохранить файл", path, error)) from None


def _describe_os_error(action: str, path: str, error: OSError) -> str:
    reason = error.strerror or str(error)
    return f"{action}:\n{path}\n\nПричина: {reason}"
