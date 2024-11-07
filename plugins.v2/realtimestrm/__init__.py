import os
from pathlib import Path
from typing import Any, List, Dict, Tuple

from app.core.event import eventmanager, Event
from app.schemas.types import EventType
from app.log import logger
from app.plugins import _PluginBase
from app.core.config import settings

class RealTimeStrm(_PluginBase):
    # Plugin metadata
    plugin_name = "实时STRM生成"
    plugin_desc = "监控入库事件，实时生成STRM文件。"
    plugin_icon = "https://s1.locimg.com/2024/11/07/06b2b87af76d0.png"
    plugin_version = "0.1"
    plugin_author = "MMZOX"
    plugin_config_prefix = "realtimestrm_"
    plugin_order = 21
    auth_level = 1

    # Private variables
    _enabled = False
    _dest_dir = None

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._dest_dir = config.get("dest_dir")

    def get_state(self) -> bool:
        return self._enabled

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
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
                                    'cols': 12
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'dest_dir',
                                            'label': 'STRM文件目录',
                                            'placeholder': '/movies/strm'
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
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '插件会监控媒体入库事件，自动在指定目录下生成对应的STRM文件。'
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
            "dest_dir": ""
        }

    @eventmanager.register(EventType.TransferComplete)
    def transfer_completed(self, event: Event):
        """
        Handle transfer complete event
        """
        if not self._enabled:
            return
        
        if not event.event_data:
            return

        # Get file info from event
        transferinfo = event.event_data.get("transferinfo")
        if not transferinfo:
            return
            
        file_list = transferinfo.file_list_new
        for file in file_list:
            file_path = Path(file)
            if not file_path.exists():
                logger.warn(f"{file_path} 不存在")
                continue
            if file_path.suffix not in settings.RMT_MEDIAEXT:
                logger.warn(f"{file_path} 不是支持的视频文件")
                continue
            self.__create_strm(file)

    def __create_strm(self, source_file: str):
        """
        Create STRM file
        """
        try:
            # Get video name
            video_name = Path(source_file).name
            
            # Create dest dir if not exists
            if not Path(self._dest_dir).exists():
                logger.info(f"创建STRM文件目录 {self._dest_dir}")
                os.makedirs(self._dest_dir)

            # Construct STRM file path
            strm_path = os.path.join(self._dest_dir, f"{os.path.splitext(video_name)[0]}.strm")
            
            # Skip if STRM exists
            if Path(strm_path).exists():
                logger.info(f"STRM文件已存在 {strm_path}")
                return

            # Write STRM file with source path
            with open(strm_path, 'w') as f:
                f.write(source_file)

            logger.info(f"创建STRM文件 {strm_path}")

        except Exception as e:
            logger.error(f"创建STRM文件失败: {str(e)}")

    def get_command(self) -> List[Dict[str, Any]]:
        return []

    def get_api(self) -> List[Dict[str, Any]]:
        return []

    def get_service(self) -> List[Dict[str, Any]]:
        return []

    def get_page(self) -> List[dict]:
        return []

    def stop_service(self):
        pass