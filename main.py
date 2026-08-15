import asyncio
import json
import os
import re

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import At
from astrbot.api.star import Context, Star, register

PLUGIN_NAME = "astrbot_plugin_ban_user"
PLUGIN_PRIORITY = 100


@register(
    PLUGIN_NAME,
    "YourName",
    "拉黑指定用户，使 Bot 不再处理其消息",
    "1.0.0",
    "https://github.com/1740443398/astrbot_plugin_ban_user",
)
class BanUserPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self._data_dir = os.path.join("data", "ban_user")
        self._ban_file = os.path.join(self._data_dir, "banned.json")
        self._banned: dict[str, str] = {}  # {user_id: reason 或 ""}
        self._lock = asyncio.Lock()
        self._loaded = False  # 防御性：避免未加载完成时误判

    async def initialize(self):
        await self._load_banned()
        self._loaded = True
        logger.info(
            f"[{PLUGIN_NAME}] 插件已初始化，当前封禁用户数: {len(self._banned)}"
        )

    async def _load_banned(self):
        """从 data 目录加载封禁列表。"""
        try:
            if not os.path.exists(self._data_dir):
                os.makedirs(self._data_dir, exist_ok=True)
            if not os.path.exists(self._ban_file):
                self._banned = {}
                await self._save_banned()
                return
            async with self._lock:
                with open(self._ban_file, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self._banned = {str(k): str(v) for k, v in data.items()}
                else:
                    self._banned = {}
        except Exception as e:
            logger.error(f"[{PLUGIN_NAME}] 加载封禁列表失败: {e}", exc_info=True)
            self._banned = {}

    async def _save_banned(self):
        """将封禁列表持久化到 data 目录。"""
        try:
            if not os.path.exists(self._data_dir):
                os.makedirs(self._data_dir, exist_ok=True)
            async with self._lock:
                with open(self._ban_file, "w", encoding="utf-8") as f:
                    json.dump(self._banned, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[{PLUGIN_NAME}] 保存封禁列表失败: {e}", exc_info=True)

    @staticmethod
    def _get_sender_id(event: AstrMessageEvent) -> str | None:
        """获取消息发送者 ID。"""
        try:
            sender = event.message_obj.sender
            if sender is None:
                return None
            uid = getattr(sender, "user_id", None)
            if uid is None:
                return None
            return str(uid)
        except Exception:
            return None

    @staticmethod
    def _is_admin(event: AstrMessageEvent) -> bool:
        """判断发送者是否为管理员/群主。"""
        try:
            sender = event.message_obj.sender
            if sender is None:
                return False
            role = getattr(sender, "role", "")
            return role in ("admin", "owner")
        except Exception:
            return False

    @staticmethod
    def _extract_target(event: AstrMessageEvent) -> str | None:
        """从消息中提取封禁目标 QQ 号。

        优先解析 @ 消息段，其次解析纯文本中的纯数字。
        """
        # 优先解析 @ 消息段
        for comp in event.get_messages():
            if isinstance(comp, At):
                qq = str(comp.qq)
                if qq and qq != "all":
                    return qq
        # 其次解析纯文本中的数字
        text = event.get_message_str()
        match = re.search(r"\d+", text)
        if match:
            return match.group()
        return None

    @staticmethod
    def _extract_reason(event: AstrMessageEvent) -> str:
        """从消息中提取封禁原因（@ 或 QQ 号之后的剩余文本）。"""
        text = event.get_message_str().strip()
        # 去掉指令前缀
        text = re.sub(r"^/?ban\s*", "", text, flags=re.IGNORECASE).strip()
        # 去掉 QQ 号
        text = re.sub(r"^\s*\d+\s*", "", text).strip()
        # 去掉 @ 消息段（转换为文本后 @ + 数字）
        text = re.sub(r"@\S*", "", text).strip()
        # 去掉可能残留的 @数字
        text = re.sub(r"@\d+\s*", "", text).strip()
        return text

    @filter.command("ban", priority=PLUGIN_PRIORITY)
    async def ban(self, event: AstrMessageEvent):
        """封禁指定用户，使其无法使用 Bot。\n
        用法: /ban @用户 或 /ban QQ号 [原因]
        """
        try:
            if not self._is_admin(event):
                yield event.plain_result("❌ 仅管理员可使用此指令。")
                return

            target = self._extract_target(event)
            if not target:
                yield event.plain_result(
                    "❌ 请指定要封禁的用户，用法: /ban @用户 或 /ban QQ号 [原因]"
                )
                return

            sender_id = self._get_sender_id(event)
            if sender_id and sender_id == target:
                yield event.plain_result("❌ 不能封禁自己。")
                return

            reason = self._extract_reason(event)
            await self._load_banned()
            self._banned[target] = reason
            await self._save_banned()

            logger.info(f"[{PLUGIN_NAME}] 用户 {target} 已被封禁")
            suffix = f"，原因: {reason}" if reason else ""
            yield event.plain_result(f"✅ 已封禁用户 {target}{suffix}")
        except Exception as e:
            logger.error(f"[{PLUGIN_NAME}] /ban 指令执行失败: {e}", exc_info=True)
            yield event.plain_result(f"封禁失败: {e}")

    @filter.command("unban", priority=PLUGIN_PRIORITY)
    async def unban(self, event: AstrMessageEvent):
        """解封指定用户。\n
        用法: /unban QQ号
        """
        try:
            if not self._is_admin(event):
                yield event.plain_result("❌ 仅管理员可使用此指令。")
                return

            target = self._extract_target(event)
            if not target:
                yield event.plain_result("❌ 请指定要解封的用户，用法: /unban QQ号")
                return

            await self._load_banned()
            if target in self._banned:
                del self._banned[target]
                await self._save_banned()
                logger.info(f"[{PLUGIN_NAME}] 用户 {target} 已解封")
                yield event.plain_result(f"✅ 已解封用户 {target}")
            else:
                yield event.plain_result(f"ℹ️ 用户 {target} 不在封禁列表中")
        except Exception as e:
            logger.error(f"[{PLUGIN_NAME}] /unban 指令执行失败: {e}", exc_info=True)
            yield event.plain_result(f"解封失败: {e}")

    @filter.command("banlist", priority=PLUGIN_PRIORITY)
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def banlist(self, event: AstrMessageEvent):
        """查看当前封禁列表。\n
        用法: /banlist
        """
        try:
            await self._load_banned()
            if not self._banned:
                yield event.plain_result("当前没有封禁的用户。")
                return
            lines = ["📋 当前封禁列表:"]
            for uid, reason in self._banned.items():
                suffix = f"（{reason}）" if reason else ""
                lines.append(f"- {uid}{suffix}")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            logger.error(f"[{PLUGIN_NAME}] /banlist 指令执行失败: {e}", exc_info=True)
            yield event.plain_result(f"查询失败: {e}")

    @filter.event_message_type(filter.EventMessageType.ALL, priority=PLUGIN_PRIORITY)
    async def on_all_message(self, event: AstrMessageEvent):
        """拦截封禁用户的所有消息，使其无法使用 Bot。"""
        try:
            if not self._loaded:
                return
            sender_id = self._get_sender_id(event)
            if not sender_id:
                return
            if sender_id in self._banned:
                # 封禁用户自身无法使用任何 Bot 功能，终止事件传播
                event.stop_event()
                logger.info(f"[{PLUGIN_NAME}] 已拦截封禁用户 {sender_id} 的消息")
        except Exception as e:
            logger.error(f"[{PLUGIN_NAME}] 拦截消息时发生错误: {e}", exc_info=True)

    async def terminate(self):
        logger.info(f"[{PLUGIN_NAME}] 插件已卸载")
