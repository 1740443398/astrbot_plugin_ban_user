# astrbot_plugin_ban_user

拉黑指定用户，使 Bot 不再处理其消息。管理员可使用 `/ban` 封禁用户（支持 `@` 用户或直接输入 QQ 号），`/unban` 解封，`/banlist` 查看封禁列表。被封禁的用户在任何情况下都无法使用 Bot。

> [!NOTE]
> 这是 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 的插件。
>
> [AstrBot](https://github.com/AstrBotDevs/AstrBot) 是一个 agentic 助手，适用于个人和群聊场景。支持部署在 QQ、Telegram、飞书、钉钉、Slack、LINE、Discord、Matrix 等数十个主流即时通讯平台。

## 功能特性

- **拉黑用户**：管理员使用 `/ban` 封禁指定用户，使其无法使用任何 Bot 功能
- **@ 或 QQ 号**：支持 `@` 用户或直接输入 QQ 号两种方式指定目标
- **封禁原因**：可选填封禁原因，便于管理记录
- **解封用户**：管理员使用 `/unban` 解封指定用户
- **查看封禁列表**：管理员使用 `/banlist` 查看当前所有封禁用户及原因
- **高优先级拦截**：插件优先级设为 100，被封禁用户的消息在第一时间被拦截并终止事件传播，任何指令、LLM 请求均无法执行
- **持久化存储**：封禁列表持久化保存到 `data/ban_user/banned.json`，重启不丢失

## 安装

将插件文件夹 `astrbot_plugin_ban_user` 放入 AstrBot 的 `data/plugins` 目录，重启 AstrBot 或重载插件即可。

## 指令说明

所有指令仅管理员（群主/管理员）可用。

### 封禁用户

```
/ban @用户 [原因]
/ban QQ号 [原因]
```

**示例：**

```
/ban @小明 广告骚扰
/ban 123456789 刷屏
```

### 解封用户

```
/unban QQ号
```

**示例：**

```
/unban 123456789
```

### 查看封禁列表

```
/banlist
```

## 工作原理

插件通过高优先级消息事件监听器（`priority=100`）监听所有消息事件。当检测到消息发送者位于封禁列表时，立即调用 `event.stop_event()` 终止事件传播，使 Bot 完全不处理该用户的消息——包括其他插件的 handler 和默认的 LLM 请求链路。

## 数据存储

封禁列表持久化保存在 `data/ban_user/banned.json` 文件中，格式为：

```json
{
    "123456789": "广告骚扰",
    "987654321": ""
}
```

## 兼容性

- 平台：aiocqhttp（QQ）
- AstrBot 版本：>=4.16, <5

## Supports

- [AstrBot Repo](https://github.com/AstrBotDevs/AstrBot)
- [AstrBot 插件开发文档（中文）](https://docs.astrbot.app/dev/star/plugin-new.html)
- [AstrBot Plugin Development Docs (English)](https://docs.astrbot.app/en/dev/star/plugin-new.html)

## 许可证

AGPL-3.0