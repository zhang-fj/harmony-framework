"""配置值注入注解"""

import os
import re
from typing import Any, Optional


def value(expression: str, default: Any = None, required: bool = True):
    """
    值注入注解

    Args:
        expression: 配置表达式，如 "${app.name}"
        default: 默认值
        required: 是否必需
    """

    def decorator(field):
        field.__harmony_value__ = {
            'expression': expression,
            'default': default,
            'required': required
        }
        return field

    return decorator


class PropertyValueResolver:
    """属性值解析器"""

    def __init__(self, properties: Optional[dict] = None):
        self.properties = properties or {}
        self.environment = dict(os.environ)

    def resolve_value(self, expression: str, default: Any = None, required: bool = True) -> Any:
        """
        解析配置表达式

        支持的表达式:
        - "app.name" - 直接属性查找
        - "${app.name}" - 环境变量插值
        - "${app.name:defaultValue}" - 带默认值的插值
        """
        if not expression:
            return default

        # 处理插值表达式
        if '${' in expression:
            return self._resolve_interpolation(expression, default, required)
        else:
            return self._resolve_direct_property(expression, default, required)

    def _resolve_interpolation(self, expression: str, default: Any, required: bool) -> Any:
        """解析插值表达式"""
        # 匹配 ${key:default} 格式
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, expression)

        # 如果是纯插值表达式（如 ${key} 或 ${key:default}），直接返回解析后的值
        if len(matches) == 1 and expression == '${' + matches[0] + '}':
            match = matches[0]
            if ':' in match:
                key, default_value = match.split(':', 1)
            else:
                key, default_value = match, default

            return self._resolve_direct_property(key.strip(), default_value, required)

        # 复杂插值表达式处理
        result = expression
        for match in matches:
            if ':' in match:
                key, default_value = match.split(':', 1)
            else:
                key, default_value = match, default

            # 解析实际值
            actual_value = self._resolve_direct_property(key.strip(), default_value, False)

            # 替换占位符
            placeholder = '${' + match + '}'
            result = result.replace(placeholder, str(actual_value))

        return result

    def _resolve_direct_property(self, key: str, default: Any, required: bool) -> Any:
        """解析直接属性"""
        # 首先从配置属性查找
        if key in self.properties:
            value = self.properties[key]
            # 如果是字符串，进行类型转换
            if isinstance(value, str):
                return self._convert_type(value)
            return value

        # 然后从环境变量查找
        env_value = self.environment.get(key)
        if env_value is not None:
            return self._convert_type(env_value)

        # 如果是必需的，抛出异常
        if required and default is None:
            raise ValueError(f"Required configuration property '{key}' not found")

        return default

    def _convert_type(self, value: str) -> Any:
        """类型转换"""
        # 布尔值
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'

        # 整数 - 处理纯数字字符串
        if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
            try:
                return int(value)
            except ValueError:
                pass

        # 浮点数
        if '.' in value and value.replace('.', '').replace('-', '').isdigit():
            try:
                return float(value)
            except ValueError:
                pass

        # JSON格式
        if value.startswith(('{', '[')):
            try:
                import json
                return json.loads(value)
            except json.JSONDecodeError:
                pass

        # 默认返回字符串
        return value

    def set_property(self, key: str, value: Any):
        """设置属性"""
        self.properties[key] = value

    def add_properties(self, properties: dict):
        """批量添加属性"""
        self.properties.update(properties)

    def load_from_file(self, file_path: str):
        """从文件加载配置"""
        if file_path.endswith('.json'):
            self._load_json(file_path)
        elif file_path.endswith(('.yml', '.yaml')):
            self._load_yaml(file_path)
        elif file_path.endswith('.properties'):
            self._load_properties(file_path)
        else:
            raise ValueError(f"Unsupported config file format: {file_path}")

    def _load_json(self, file_path: str):
        """加载JSON配置文件"""
        import json
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                self.properties.update(self._flatten_dict(data))

    def _load_yaml(self, file_path: str):
        """加载YAML配置文件"""
        try:
            import yaml
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict):
                    self.properties.update(self._flatten_dict(data))
        except ImportError:
            raise ImportError("PyYAML is required for YAML configuration support")

    def _load_properties(self, file_path: str):
        """加载Properties格式配置文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        self.properties[key.strip()] = value.strip()

    def _flatten_dict(self, data: dict, prefix: str = '') -> dict:
        """扁平化嵌套字典"""
        result = {}
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                result.update(self._flatten_dict(value, full_key))
            else:
                result[full_key] = value
        return result
