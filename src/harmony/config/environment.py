"""环境管理"""

import os
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List


class Environment(Enum):
    """环境类型"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class EnvironmentManager:
    """环境管理器"""

    def __init__(self):
        self.current_environment = self._detect_environment()
        self.active_profiles = self._determine_active_profiles()
        self.properties: Dict[str, Any] = {}

    def _detect_environment(self) -> Environment:
        """检测当前环境"""
        env_name = os.getenv('ENVIRONMENT', os.getenv('SPRING_PROFILES_ACTIVE', 'development')).lower()

        env_mapping = {
            'dev': Environment.DEVELOPMENT,
            'development': Environment.DEVELOPMENT,
            'test': Environment.TESTING,
            'testing': Environment.TESTING,
            'stage': Environment.STAGING,
            'staging': Environment.STAGING,
            'prod': Environment.PRODUCTION,
            'production': Environment.PRODUCTION,
        }

        return env_mapping.get(env_name, Environment.DEVELOPMENT)

    def _determine_active_profiles(self) -> List[str]:
        """确定活跃的配置文件"""
        profiles = os.getenv('SPRING_PROFILES_ACTIVE', '')
        if profiles:
            return [profile.strip() for profile in profiles.split(',')]
        return [self.current_environment.value]

    def get_environment(self) -> Environment:
        """获取当前环境"""
        return self.current_environment

    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.current_environment == Environment.DEVELOPMENT

    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.current_environment == Environment.PRODUCTION

    def is_testing(self) -> bool:
        """是否为测试环境"""
        return self.current_environment == Environment.TESTING

    def add_profile(self, profile: str):
        """添加配置文件"""
        if profile not in self.active_profiles:
            self.active_profiles.append(profile)

    def get_active_profiles(self) -> List[str]:
        """获取所有活跃的配置文件"""
        return self.active_profiles.copy()

    def is_profile_active(self, profile: str) -> bool:
        """检查配置文件是否活跃"""
        return profile in self.active_profiles

    def get_property_source_priority(self) -> List[str]:
        """获取属性源的优先级顺序"""
        return [
            'command_line',
            'environment_variables',
            f'application-{self.current_environment.value}',
            'application',
            'default'
        ]

    def load_config_files(self, config_dir: str = "config"):
        """加载配置文件"""
        config_path = Path(config_dir)
        if not config_path.exists():
            return

        # 加载基础配置文件
        base_file = config_path / "application.yml"
        if base_file.exists():
            self._load_config_file(base_file)

        # 加载环境特定配置文件
        env_file = config_path / f"application-{self.current_environment.value}.yml"
        if env_file.exists():
            self._load_config_file(env_file)

        # 加载活跃profile的配置文件
        for profile in self.active_profiles:
            if profile != self.current_environment.value:
                profile_file = config_path / f"application-{profile}.yml"
                if profile_file.exists():
                    self._load_config_file(profile_file)

    def _load_config_file(self, file_path: Path):
        """加载单个配置文件"""
        try:
            import yaml
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict):
                    self._flatten_and_merge(data, file_path.stem)
        except ImportError:
            print(f"Warning: PyYAML is required to load {file_path}")
        except Exception as e:
            print(f"Warning: Failed to load {file_path}: {e}")

    def _flatten_and_merge(self, data: dict, source: str):
        """扁平化并合并配置"""

        def flatten(d: dict, prefix: str = '') -> dict:
            result = {}
            for key, value in d.items():
                new_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    result.update(flatten(value, new_key))
                else:
                    result[new_key] = value
            return result

        flattened = flatten(data)
        for key, value in flattened.items():
            self.properties[key] = value
            # 同时设置到环境变量中，便于其他地方使用
            os.environ[f"HARMONY_{key.upper().replace('.', '_')}"] = str(value)

    def get_property(self, key: str, default: Any = None) -> Any:
        """获取配置属性"""
        return self.properties.get(key, default)

    def set_property(self, key: str, value: Any):
        """设置配置属性"""
        self.properties[key] = value

    def get_all_properties(self) -> Dict[str, Any]:
        """获取所有配置属性"""
        return self.properties.copy()


# 全局环境管理器实例
environment_manager = EnvironmentManager()
