# HiSMap - 古代游记地图 设计文档

## 概述

HiSMap 是一个 Web 端旅游地图应用，将古代书籍中记载的游记映射到地图上，方便人们在旅游时查阅。支持桌面端和移动端，兼容国内外不同地图源。

## 技术栈

| 层 | 技术 | 用途 |
|---|---|---|
| 前端框架 | React 18 + TypeScript | UI 构建 |
| 构建工具 | Vite | 开发服务器 + 构建 |
| 地图 | react-leaflet + OpenStreetMap | 地图渲染和交互 |
| 状态管理 | React Query (TanStack Query) | API 数据缓存和状态 |
| UI 组件 | shadcn/ui 或 Ant Design | 基础 UI 组件 |
| 后端框架 | FastAPI | REST API |
| ORM | SQLAlchemy 2.0 | 数据库操作 |
| 数据库 | PostgreSQL + PostGIS | 数据存储 + 地理查询 |
| 认证 | python-jose (JWT) | Admin API 认证 |
| 迁移 | Alembic | 数据库 schema 迁移 |

## 数据模型

### 实体

#### Book（书籍）
- `id`: 主键
- `title`: 书名
- `author`: 作者
- `dynasty`: 朝代
- `era_start`: 起始年份
- `era_end`: 结束年份
- `description`: 简介
- `source_text`: 原始文本来源

#### Author（作者）
- `id`: 主键
- `name`: 姓名
- `dynasty`: 朝代
- `birth_year`: 出生年
- `death_year`: 去世年
- `biography`: 生平简介

#### Location（地点）
- `id`: 主键
- `name`: 名称
- `modern_name`: 现代地名
- `ancient_name`: 古代地名
- `latitude`: 纬度
- `longitude`: 经度
- `geom`: PostGIS geometry 字段
- `location_type`: 地点类型（山川/古城/寺庙/关隘/...）
- `ancient_region`: 所属古代区域（如"丝绸之路·河西走廊"）
- `one_line_summary`: 一句话摘要
- `location_rationale`: 古今对应依据
- `academic_disputes`: 学术争议
- `credibility_notes`: 可信度分析
- `today_remains`: 今日遗迹

#### JournalEntry（游记条目）—— 核心实体
- `id`: 主键
- `book_id`: 关联书籍
- `title`: 条目标题
- `original_text`: 原文
- `modern_translation`: 白话译文
- `english_translation`: 英文译文
- `chapter_reference`: 章节引用（如"第2卷第38章"）
- `keywords`: 关键词数组（JSON 字段）
- `keyword_annotations`: 关键词标注（JSON，含位置信息）
- `era_context`: 时代背景（如"地理大发现"/"十字军东征"/"启蒙运动"）
- `political_context`: 政治背景
- `religious_context`: 宗教历史
- `social_environment`: 社会环境
- `visit_date_approximate`: 大致游览时间

### 关联表

- `entry_locations`: 游记-地点关联，含 `location_order`（游记中的访问顺序）
- `entry_authors`: 游记-作者关联
- `relation_locations`: 地点-地点关联，含 `relation_type`（关系类型，如"贸易路线"/"同一区域"）和 `description`（关系描述）

## 系统架构

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (Vite + React + TS)       │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Map View  │  │ Search   │  │ Filter Panel     │   │
│  │ (Leaflet) │  │ Bar      │  │ (dynasty/author) │   │
│  └──────────┘  └──────────┘  └──────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │ Entry Detail Panel (drawer/modal)            │   │
│  └──────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────┘
                        │ REST API (JSON)
┌───────────────────────┴─────────────────────────────┐
│                 Backend (FastAPI)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ /api/     │  │ /api/    │  │ /api/entries     │   │
│  │ locations │  │ search   │  │ /api/authors     │   │
│  └──────────┘  └──────────┘  │ /api/books       │   │
│                              └──────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │ Admin API (CMS 后台)                         │   │
│  └──────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────┴─────────────────────────────┐
│              PostgreSQL + PostGIS                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Books    │  │ Authors  │  │ JournalEntries   │   │
│  │ Locations│  │ entry_   │  │ entry_authors    │   │
│  │          │  │ locations│  │                  │   │
│  └──────────┘  └──────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────┘
```

前后端分离，通过 REST API 通信。后端同时服务前端应用和 CMS 后台。PostGIS 处理地理空间查询。前端独立部署为静态资源，后端单独部署。

## API 设计

### 前端 API（公开接口，无需认证）

| 方法 | 路径 | 说明 | 查询参数 |
|------|------|------|----------|
| GET | `/api/locations` | 所有地点（含坐标） | `?type=山川&dynasty=唐` |
| GET | `/api/locations/{id}` | 单个地点详情 | 含游记条目、关联地点、现代解释 |
| GET | `/api/entries` | 游记列表 | `?dynasty=&author=&keyword=&era=` |
| GET | `/api/entries/{id}` | 单条游记详情 | |
| GET | `/api/authors` | 作者列表 | `?dynasty=` |
| GET | `/api/authors/{id}` | 作者详情 | 含关联游记 |
| GET | `/api/books` | 书籍列表 | |
| GET | `/api/books/{id}` | 书籍详情 | 含所有条目 |
| GET | `/api/search` | 全文搜索 | `?q=关键词`（搜索原文、译文、关键词、背景） |
| GET | `/api/filters` | 所有可用筛选选项 | 返回朝代列表、作者列表、地点类型 |

### Admin API（CMS 后台，JWT 认证）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/admin/entries` | 新增游记 |
| PUT | `/api/admin/entries/{id}` | 编辑游记 |
| DELETE | `/api/admin/entries/{id}` | 删除游记 |
| POST | `/api/admin/locations` | 新增地点 |
| PUT | `/api/admin/locations/{id}` | 编辑地点 |
| POST | `/api/admin/locations/{id}/relations` | 新增地点关联 |
| DELETE | `/api/admin/locations/{id}/relations/{rid}` | 删除地点关联 |
| POST | `/api/admin/authors` | 新增作者 |
| POST | `/api/admin/books` | 新增书籍 |

## UI/UX 设计

### 桌面端布局

- 顶部导航栏：Logo + 搜索框 + 筛选按钮
- 左侧面板：筛选条件 + 结果列表（可折叠）
- 右侧区域：地图（占满剩余空间）
- 底部/右侧滑出面板：游记详情

### 移动端布局

- 顶部：搜索框 + 筛选图标
- 主体：全屏地图
- 底部抽屉：结果列表 / 游记详情（可上滑展开）
- 筛选：弹出层

### 响应式断点

- 768px：移动端/桌面端切换
- 桌面端左右分栏，移动端全屏地图 + 底部抽屉

### 交互流程

1. **浏览模式**：地图加载后显示所有标记点，点击标记弹出简要信息（书名+作者+朝代）
2. **详情查看**：点击简要信息展开详情面板或进入地点页面
3. **筛选**：选择朝代、作者、地点类型后实时更新地图标记
4. **搜索**：输入关键词，搜索结果在列表中显示，点击定位到地图

### 地点详情页设计（四层结构）

地点详情页是应用的核心内容页，分为四个层次递进展示：

#### 第一层：快速理解

页面顶部，帮助用户在 10 秒内理解这个地点：

- 现代地图位置（小地图 + 坐标）
- 古代地名 vs 现代地名
- 所属古代区域（如"丝绸之路·河西走廊"）
- 相关旅行者头像/名字列表（点击跳转）
- 出现章节/书籍链接
- 一句话摘要（如"马可·波罗描述的东方大港，当时世界最大的贸易中心之一"）

#### 第二层：原文与译文

按旅行者分组，每个旅行者一个卡片：

```
┌──────────────────────────────────────────┐
│  马可·波罗（Marco Polo）· 1292年          │
│  《马可·波罗游记》第2卷第38章              │
├──────────────────────────────────────────┤
│  [原文] [英文译文] [中文译文]  ← tab 切换  │
│                                          │
│  "在这座城市里，你可以找到所有你能想到     │
│   的香料和宝石……"                         │
│                                          │
│  关键词：香料 | 宝石 | 港口 | 贸易 | 人口  │
└──────────────────────────────────────────┘
```

**版权策略（重要）**：
- v1 阶段优先使用公版英文译本（如 Yule 译本、Marsden 译本等）
- 使用自己整理的摘要和短引用（合理使用范围内）
- 自己翻译的中文片段
- 标注来源和译者信息
- 产品成熟后再考虑获取现代译本授权

#### 第三层：现代解释

学术性内容，帮助用户理解历史背景：

- **古今对应**：为什么确认这个古代地名对应今天的地点，依据是什么
- **学术争议**：是否存在不同说法，主流观点是什么
- **可信度分析**：旅行者是否有夸张、误记、转述或想象的成分
- **政治背景**：当时谁统治这里，政治局势如何
- **贸易网络**：这个地点在当时贸易路线中的位置
- **今日遗迹**：今天还能看到什么遗迹或相关景点

#### 第四层：关系网络

可视化的关系图，展示这个地点连接的历史网络：

- 相关地点列表（点击跳转，如桑给巴尔 → 基尔瓦、蒙巴萨、亚丁）
- 贸易路线（在地图上高亮显示）
- 贸易商品（黄金、象牙、香料等）
- 相关人物（商人、统治者、传教士等）
- 连接到的更大网络（如"印度洋贸易网络"）

关系网络可以用两种方式呈现：
- **列表式**：简单的关联卡片，v1 实现
- **图谱式**：节点-连线可视化图，后续迭代

### 地点详情页数据模型扩展

Location 实体需要扩展以下字段：

```
Location（地点）扩展字段
├── ancient_region: 所属古代区域（如"丝绸之路·河西走廊"）
├── one_line_summary: 一句话摘要
├── modern_explanation: 现代解释
│   ├── location_rationale: 古今对应依据
│   ├── academic_disputes: 学术争议
│   ├── credibility_notes: 可信度分析
│   └── today_remains: 今日遗迹
└── related_locations: 关联地点（通过 relation_locations 关联表）
    ├── related_location_id: 关联地点 ID
    ├── relation_type: 关系类型（贸易路线/同一区域/...）
    └── description: 关系描述
```

游记条目扩展：

```
JournalEntry 扩展字段
├── english_translation: 英文译文
├── chapter_reference: 章节引用（如"第2卷第38章"）
└── keyword_annotations: 关键词标注（JSON，含位置信息）
```

## 项目结构

```
hismap/
├── frontend/                # 前端
│   ├── src/
│   │   ├── components/      # React 组件
│   │   │   ├── Map/         # 地图相关组件
│   │   │   ├── Panel/       # 侧面板、详情面板
│   │   │   ├── Search/      # 搜索组件
│   │   │   └── Filter/      # 筛选组件
│   │   ├── hooks/           # 自定义 hooks
│   │   ├── api/             # API 调用封装
│   │   ├── types/           # TypeScript 类型定义
│   │   └── utils/           # 工具函数
│   ├── package.json
│   └── vite.config.ts
├── backend/                 # 后端
│   ├── app/
│   │   ├── api/             # 路由
│   │   ├── models/          # SQLAlchemy 模型
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── crud/            # 数据库操作
│   │   └── core/            # 配置、认证
│   ├── alembic/             # 数据库迁移
│   ├── requirements.txt
│   └── pyproject.toml
└── docs/                    # 文档和设计稿
```

## 地图适配策略

- v1 阶段使用 OpenStreetMap 瓦片源
- 后续适配国内地图源（高德/百度），通过地图 provider 抽象层实现
- 瓦片源切换不影响业务逻辑和数据模型

## 范围说明

### v1 范围
- 地图浏览和标记
- 地点详情页（四层结构：快速理解、原文与译文、现代解释、关系网络）
- 朝代/作者/类型筛选
- 关键词搜索
- CMS 后台（基础 CRUD）
- 响应式布局（桌面+移动）

### 后续迭代
- 数据处理管线（原始古籍文本 → 结构化数据）
- 国内地图源适配
- 时间线视图
- 用户系统（登录、收藏、评论）
- 关系网络图谱可视化（节点-连线）
