"""通用工具函数"""
import json


def _to_plain(obj):
    """将对象转换为可序列化的普通 Python 类型"""
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, list):
        return [_to_plain(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _to_plain(value) for key, value in obj.items()}

    if hasattr(obj, "model_dump"):
        try:
            return _to_plain(obj.model_dump())
        except Exception:
            pass

    plain = {}
    for key in (
        "type",
        "id",
        "name",
        "text",
        "input",
        "stop_reason",
        "role",
        "content",
    ):
        if hasattr(obj, key):
            plain[key] = _to_plain(getattr(obj, key))
    if plain:
        return plain

    return str(obj)


def pretty_print(label: str, data, max_chars: int = 4000) -> None:
    """
    格式化打印数据（主要用于调试）

    Args:
        label: 打印的标签前缀
        data: 要打印的数据（支持对象、字典、列表等）
        max_chars: 最大字符数，超出部分会被截断
    """
    try:
        rendered = json.dumps(_to_plain(data), ensure_ascii=False, indent=2)
    except Exception:
        rendered = str(data)
    if len(rendered) > max_chars:
        rendered = rendered[:max_chars] + "\n... (truncated)"
    print(f"{label}\n{rendered}")
