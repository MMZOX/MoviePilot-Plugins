import os
from pathlib import Path
from typing import Any, List, Dict, Tuple
from datetime import datetime

from app.core.event import eventmanager
from app.schemas.types import EventType
from app.log import logger
from app.plugins import _PluginBase
from app.modules.filemanager import FileManagerModule

class RealTimeStrm(_PluginBase):
    # Plugin metadata
    plugin_name = "实时STRM生成"
    plugin_desc = "监控入库事件，实时生成STRM文件。"
    plugin_icon = "https://s1.locimg.com/2024/11/07/06b2b87af76d0.png"
    plugin_version = "0.23"
    plugin_author = "MMZOX"
    plugin_config_prefix = "realtimestrm_"
    plugin_order = 22
    auth_level = 1

    # Private attributes
    _enabled = False
    _dest_dir = None
    _replace_prefix = None
    _target_prefix = None
    _cloud_type = None
    _cloud_client = None
    _download_extra = False
    _filemanager = None
    _history = []
    
    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._dest_dir = config.get("dest_dir")
            self._replace_prefix = config.get("replace_prefix")
            self._target_prefix = config.get("target_prefix")
            self._cloud_type = config.get("cloud_type")
            self._download_extra = config.get("download_extra")
            
        # Initialize FileManager module
        self._filemanager = FileManagerModule()
        self._filemanager.init_module()
        
        # Load history
        self._history = self.get_data('history') or []

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        Get plugin form
        """
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSelect',
                                        'props': {
                                            'model': 'cloud_type',
                                            'label': '云盘类型',
                                            'items': [
                                                {'title': '阿里云盘', 'value': 'aliyundrive'},
                                                {'title': '115网盘', 'value': '115'}
                                            ]
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'replace_prefix',
                                            'label': '替换前缀',
                                            'placeholder': '要替换的路径前缀，如 MediaV2'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'target_prefix',
                                            'label': '目标前缀',
                                            'placeholder': '替换后的路径前缀，如 CloudASJ'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'download_extra',
                                            'label': '下载额外文件',
                                            'hint': '下载字幕、图片等额外文件'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "cloud_type": "aliyundrive",
            "replace_prefix": "",
            "target_prefix": "",
            "download_extra": False
        }

    def __create_strm(self, transfer_info):
        """Create STRM file"""
        try:
            if not transfer_info.target_item:
                return
                
            file_path = Path(transfer_info.target_item.path)
            strm_path = Path(self._dest_dir) / file_path.relative_to(self._replace_prefix if self._replace_prefix else file_path.parts[0])
            strm_path = strm_path.with_suffix('.strm')
            
            # Create parent directory
            os.makedirs(strm_path.parent, exist_ok=True)
            
            # Generate STRM content
            strm_content = transfer_info.target_item.path
            if self._replace_prefix and strm_content.startswith(self._replace_prefix):
                strm_content = strm_content[len(self._replace_prefix):].lstrip('/')
                if self._target_prefix:
                    strm_content = f"{self._target_prefix}/{strm_content}"
            elif self._target_prefix:
                strm_content = f"{self._target_prefix}/{strm_content}"

            # Write STRM file
            with open(strm_path, 'w', encoding='utf-8') as f:
                f.write(strm_content)

            logger.info(f"创建STRM文件 {strm_path}")

            # Handle extra files if enabled
            if self._download_extra:
                self.__handle_extra_files(transfer_info)

        except Exception as e:
            logger.error(f"创建STRM文件失败: {str(e)}")

    def __handle_extra_files(self, transfer_info):
        """Handle downloading extra files like subtitles and images"""
        try:
            if not transfer_info.target_diritem:
                logger.debug("未获取到目标目录信息，跳过下载额外文件")
                return
                
            logger.info(f"开始检索目录额外文件：{transfer_info.target_diritem.path}")
            
            # List all files in the directory
            files = self._filemanager.list_files(transfer_info.target_diritem)
            if not files:
                logger.debug(f"目录 {transfer_info.target_diritem.path} 中没有找到文件")
                return
                
            extra_count = 0
            for file in files:
                if file.extension.lower() in ['srt', 'ass', 'ssa', 'jpg', 'png']:
                    dest_path = Path(self._dest_dir) / Path(file.path).relative_to(
                        self._replace_prefix if self._replace_prefix else Path(file.path).parts[0]
                    )
                    
                    if dest_path.exists():
                        logger.debug(f"文件已存在，跳过：{dest_path}")
                        continue
                        
                    logger.info(f"发现额外文件：{file.path}")
                    os.makedirs(dest_path.parent, exist_ok=True)
                    
                    if self._filemanager.download_file(file, dest_path):
                        extra_count += 1
                        logger.info(f"下载额外文件成功：{dest_path}")
                    else:
                        logger.error(f"下载额外文件失败：{dest_path}")

            if extra_count:
                logger.info(f"共下载 {extra_count} 个额外文件")
            else:
                logger.debug("未找到需要下载的额外文件")

        except Exception as e:
            logger.error(f"处理额外文件失败: {str(e)}")

    @eventmanager.register(EventType.TransferComplete)
    def handle_transfer_complete(self, event):
        """Handle transfer complete event"""
        try:
            if not self._enabled:
                return
                
            logger.info(f"收到入库事件，开始处理：{event}")
            
            transfer_info = event.get("transfer_info")
            if not transfer_info:
                logger.error("转移信息为空")
                return
                
            if self._download_extra:
                self.__handle_extra_files(transfer_info)
                
            # Save history like RssSubscribe
            self._history.append({
                "title": transfer_info.title,
                "path": str(transfer_info.target_item.path) if transfer_info.target_item else "",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            self.save_data('history', self._history)
                
        except Exception as e:
            logger.error(f"处理入库事件异常: {str(e)}")