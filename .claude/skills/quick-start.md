---
name: quick-start
description: 项目快速上手指南 — 帮助新人用最短时间理解项目全貌、跑通项目、开始开发
---

# 电子商务平台数据分析 — 项目快速上手指南

---

## 1. 项目核心概览

**一句话描述**：一个 Python 爬虫+数据分析学习项目，通过 Selenium 自动抓取淘宝、京东、拼多多三大电商平台的商品数据（价格、销量），用 Pandas/Matplotlib 做可视化分析，并将结果存入 MySQL 数据库。

- **核心问题**：帮助数据分析初学者理解「数据采集 → 清洗 → 分析 → 可视化 → 存储」的完整链路
- **业务价值**：对比同一商品在不同平台的定价和销量差异，辅助定价决策
- **面向用户**：数据分析初学者、Python 爬虫学习者

---

## 2. 核心功能范围

### 核心必看功能 ★

| 模块 | 说明 | 对应方法 |
|------|------|---------|
| **数据采集** | Selenium + BeautifulSoup 爬取三大平台商品 | `get_taobao_data()` `get_jd_data()` `get_pinduoduo_data()` |
| **数据处理** | Pandas DataFrame 清洗和结构化 | `run()` 中 `pd.DataFrame(all_data)` |
| **可视化分析** | Matplotlib 生成柱状图+双Y轴折线图 | `visualize_data()` |
| **数据持久化** | 存入 MySQL 数据库 | `save_to_mysql()` `create_database_table()` |

### 扩展功能

| 模块 | 说明 | 版本 |
|------|------|------|
| **CSV 导出** | 将数据导出为 CSV 文件 | V1.3 新增 |
| **命令行参数** | argparse 支持命令行传参 | V1.2 新增 |
| **交互式输入** | input() 交互式配置参数 | V1.1 新增 |

---

## 3. 技术栈全景

### 语言与运行时

| 技术 | 作用 | 优先级 |
|------|------|--------|
| **Python 3.7+** | 唯一开发语言 | 🔴 必须掌握 |

### 核心依赖库

| 库 | 在项目中的作用 | 新人需掌握程度 |
|----|--------------|--------------|
| **selenium** | 模拟浏览器操作，加载页面、执行滚动、等待元素 | 🔴 理解 WebDriver 生命周期 |
| **beautifulsoup4** | 解析 HTML，提取价格/销量 DOM 元素 | 🔴 理解 find/find_all |
| **pandas** | 用 DataFrame 组织爬取的结构化数据 | 🟡 基本使用即可 |
| **matplotlib** | 生成柱状图和双Y轴折线图 | 🟡 基本使用即可 |
| **pymysql** | 连接 MySQL，建库建表，批量 insert | 🟡 基本 CRUD |
| **numpy** | matplotlib 的底层依赖，生成坐标数组 | 🟢 了解即可 |

### 外部依赖

| 依赖 | 作用 | 注意事项 |
|------|------|---------|
| **Chrome 浏览器** | Selenium 的驱动目标 | 必须安装最新版 |
| **ChromeDriver** | Selenium 与 Chrome 的桥梁 | ⚠️ **版本必须与 Chrome 完全匹配** |
| **MySQL** | 数据落地存储 | 本地安装，默认 root/123456 |

### 部署/工具

| 工具 | 作用 |
|------|------|
| pip | 包管理 |
| Git Bash（Windows） | 运行脚本的终端 |

---

## 4. 整体架构与模块关系

```
┌─────────────────────────────────────────────────────┐
│                    if __name__ == "__main__"         │
│  入口：参数解析 (argparse/input) → 创建实例 → run()  │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              ECommerceScraper 类                     │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ 数据采集层    │  │ 数据处理层   │  │ 输出层     │ │
│  │              │  │              │  │           │ │
│  │ get_taobao   │  │              │  │ visualize │ │
│  │   _data()    │  │ run() 方法   │  │ _data()   │ │
│  │              │  │   ↓         │  │           │ │
│  │ get_jd       │  │ pd.DataFrame│  │ save_to   │ │
│  │   _data()    │──│   ↓         │──│ _mysql()  │ │
│  │              │  │ visualize() │  │           │ │
│  │ get_pinduo   │  │ save_to     │  │ CSV导出   │ │
│  │   duo_data() │  │   _mysql()  │  │           │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │ 基础设施层                                     │   │
│  │ init_driver() / close_driver()               │   │
│  │ create_database_table()                      │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### 模块依赖关系

```
main() 入口
  └─► ECommerceScraper(db_config)
        ├─► run(keyword, max_items_per_platform)
        │     ├─► get_all_data()
        │     │     ├─► get_taobao_data()    ──► init_driver() → WebDriver
        │     │     ├─► get_jd_data()        ──► init_driver() → WebDriver
        │     │     └─► get_pinduoduo_data() ──► 独立创建 WebDriver（未复用 init_driver）
        │     ├─► visualize_data(df)          ──► matplotlib → 图表 + PNG
        │     └─► save_to_mysql(all_data)
        │           └─► create_database_table() ──► pymysql → MySQL
        └─► CSV 导出（V1.3）
```

> ⚠️ **已知问题**：`get_pinduoduo_data()` 没有使用 `self.init_driver()`，而是内部独立创建 driver，代码风格不一致，且不会自动关闭 driver（手动 `driver.quit()`）。

---

## 5. 核心业务主流程

### 流程一：完整数据采集→分析→存储（唯一主流程）

```
用户启动脚本
  │
  ├─ 1. 参数解析
  │    ├─ 命令行有传参 → 使用 argparse 参数
  │    └─ 命令行无传参 → 交互式 input() 提示输入（有默认值）
  │    输出: db_config, keyword, max_items
  │
  ├─ 2. 创建爬虫实例
  │    scraper = ECommerceScraper(db_config)
  │
  ├─ 3. 执行 run()
  │    │
  │    ├─ 3.1 淘宝数据采集
  │    │    ├─ 启动 Chrome（非无头模式）
  │    │    ├─ 打开 https://s.taobao.com/search?q={keyword}
  │    │    ├─ ⏳ 等待用户扫码登录（60秒超时）
  │    │    ├─ 等待商品卡片出现
  │    │    ├─ 滚动页面 3 次加载更多
  │    │    ├─ BS4 解析 HTML → 提取价格+销量
  │    │    └─ 关闭浏览器
  │    │
  │    ├─ 3.2 京东数据采集（同上流程，网页结构不同）
  │    │    ├─ 打开 https://search.jd.com/Search?keyword={keyword}
  │    │    └─ 等待元素 #J_goodsList
  │    │
  │    ├─ 3.3 拼多多数据采集
  │    │    ├─ 打开移动版 https://mobile.yangkeduo.com/search_result.html
  │    │    └─ ⚠️ 不需要登录，但可能被反爬
  │    │
  │    ├─ 3.4 数据汇总 → pd.DataFrame
  │    │
  │    ├─ 3.5 可视化
  │    │    ├─ 柱状图：各平台平均价格对比
  │    │    ├─ 双Y轴折线图：平均价格+总销量
  │    │    └─ 保存 PNG → 屏幕显示
  │    │
  │    ├─ 3.6 MySQL 存储
  │    │    ├─ 建库 product_data（如不存在）
  │    │    ├─ 建表 products（如不存在）
  │    │    └─ 批量 INSERT
  │    │
  │    └─ 3.7 CSV 导出（V1.3）
  │         └─ 文件名: product_data_{keyword}_{时间戳}.csv
  │
  └─ 4. 完成 ✅
```

### 关键节点标注

| 节点 | 说明 | 可能的阻塞点 |
|------|------|------------|
| **扫码登录** | 淘宝和京东需要手动扫码 | 超时会导致该平台数据为空 |
| **页面元素等待** | WebDriverWait 等待特定 CSS 选择器 | 页面结构变化会导致超时 |
| **销量文本清洗** | "1万+" → 10000 的转换 | 平台改文案格式会导致解析为 0 |
| **数据库连接** | 依赖本地 MySQL 服务 | MySQL 未启动或密码错误 |

---

## 6. 项目目录与关键文件

### 当前目录结构

```
f:\github-Data_Analysis-main\
├── README.md                        # 项目说明文档
├── LICENSE                          # 木兰宽松许可证 v2
├── Product_Analysis_V1.0.py         # ← 入门阅读首选（基础版，最简洁）
├── Product_Analysis_V1.1.py         #    +交互式 input()
├── Product_Analysis_V1.2.py         #    +argparse 命令行参数
├── Product_Analysis_V1.3.py         #    +CSV导出、argparse+input兼用 ★ 最新版
└── .claude/
    └── skills/
        └── quick-start.md           # 本文件
```

### 优先阅读顺序

```
第 1 步: README.md              （10分钟 — 了解项目背景）
第 2 步: Product_Analysis_V1.0.py （30分钟 — 理解核心逻辑，结构最简单）
第 3 步: Product_Analysis_V1.3.py （20分钟 — 对比差异，了解演进方向，注意 import keyword bug）
```

### 关键代码定位

| 你要找什么 | 去哪个方法 | 行号参考（V1.3） |
|-----------|-----------|-----------------|
| **程序入口** | `if __name__ == "__main__"` | 第 421 行 |
| **完整执行流程** | `run()` | 第 390 行 |
| **WebDriver 初始化** | `init_driver()` | 第 31 行 |
| **数据采集-淘宝** | `get_taobao_data()` | 第 54 行 |
| **数据采集-京东** | `get_jd_data()` | 第 111 行 |
| **数据采集-拼多多** | `get_pinduoduo_data()` | 第 171 行 |
| **可视化** | `visualize_data()` | 第 266 行 |
| **数据库建表** | `create_database_table()` | 第 316 行 |
| **数据入库** | `save_to_mysql()` | 第 354 行 |
| **CSV 导出** | `run()` 末尾 | 第 413 行 |

---

## 7. 本地启动与调试

### 7.1 环境准备（一次性）

```bash
# 1. 确认 Python 版本 >= 3.7
python --version

# 2. 安装依赖库
pip install pandas matplotlib pymysql beautifulsoup4 selenium numpy

# 3. 确认 Chrome 浏览器已安装最新版
#    下载地址: https://www.google.com/chrome/

# 4. 安装 ChromeDriver
#    下载地址: https://chromedriver.chromium.org/
#    ⚠️ 版本号必须与 Chrome 一致！
#    查看 Chrome 版本: 浏览器地址栏输入 chrome://version
#    下载后将 chromedriver.exe 放到 PATH 目录或项目目录

# 5. 安装并启动 MySQL
#    默认配置: root / 123456
#    确认服务已启动: net start mysql  (Windows)
```

### 7.2 启动项目

```bash
# 切到项目目录
cd f:\github-Data_Analysis-main

# 运行最新版（命令行参数模式）
python Product_Analysis_V1.3.py --keyword huaweipurax --max_items 5

# 或运行最新版（交互模式，不传参数即触发）
python Product_Analysis_V1.3.py

# 或运行最简版（快速验证）
python Product_Analysis_V1.0.py
```

### 7.3 验证成功标志

- ✅ 自动打开 Chrome 浏览器，跳转到淘宝/京东/拼多多搜索页
- ✅ 终端提示「请在60秒内扫码登录...」
- ✅ 扫码后终端输出「成功获取N条XX数据」
- ✅ 弹出 matplotlib 图表窗口
- ✅ 终端输出「成功保存 N 条数据到MySQL数据库」
- ✅ 终端输出「程序执行完毕!」

### 7.4 常见启动报错

| 报错信息 | 原因 | 解决方案 |
|---------|------|---------|
| `selenium.common.exceptions.WebDriverException: 'chromedriver' executable needs to be in PATH` | ChromeDriver 未安装或不在 PATH | 下载匹配版本的 ChromeDriver，放到项目目录或加入 PATH |
| `This version of ChromeDriver only supports Chrome version XX` | ChromeDriver 与 Chrome 版本不匹配 | 下载与 Chrome 版本一致的 ChromeDriver |
| `pymysql.err.OperationalError: (2003, "Can't connect to MySQL server")` | MySQL 服务未启动 | Windows: `net start mysql` |
| `pymysql.err.OperationalError: (1045, "Access denied")` | 数据库用户名/密码错误 | 检查代码中的 db_config 或运行时传入正确参数 |
| `No module named 'pandas'` | 依赖未安装 | `pip install pandas matplotlib pymysql beautifulsoup4 selenium numpy` |
| `Message: element not interactable` | 页面元素尚未加载完成 | 增加 WebDriverWait 的超时时间 |
| 淘宝/京东一直停在登录页 | 未扫码或扫码超时 | 60秒内完成扫码，超时该平台返回空数据 |
| 拼多多返回 0 条数据 | 可能被反爬 | 增加 `time.sleep()` 等待时间，或检查页面结构是否变化 |

---

## 8. 开发与协作规范

### 代码规范

| 方面 | 当前情况 | 建议 |
|------|---------|------|
| **命名** | 类名驼峰 `ECommerceScraper`，方法名蛇形 `get_taobao_data` | ✅ 基本符合 PEP 8 |
| **注释** | 有中文注释但不够系统 | 建议在关键方法上补充 docstring |
| **重复代码** | 4 个版本文件重复率 > 95% | 建议合并为单文件，用 git 管理版本 |
| **硬编码** | 数据库密码、CSS 选择器写死在代码中 | 建议提取为配置文件 |
| **BUG** | V1.3 第 1 行 `import keyword` 错误导入了 Python 内置 keyword 模块 | 应删除该行（`keyword` 在方法签名中作为参数名使用，不需要导入） |

### 版本管理

| 方面 | 当前情况 | 建议 |
|------|---------|------|
| **Git** | ❌ 未初始化 | 建议 `git init` 并做初始提交 |
| **版本策略** | 手动复制文件命名 V1.0/V1.1/V1.2/V1.3 | 建议用 git tag 替代 |

### 分支管理建议

```
main          ← 稳定版本
  └─ dev      ← 开发分支
       ├─ feature/xxx
       └─ fix/xxx
```

### 提交信息格式建议

```
feat: 新增功能描述
fix: 修复问题描述
docs: 文档更新
refactor: 代码重构
```

### 新人开发注意事项

1. **不要直接改 V1.0~V1.3 的原始文件**，建议以 V1.3 为基础创建 `main.py` 再修改
2. **测试爬虫时先用小数据量**（`--max_items 3`），避免触发反爬
3. **不要在代码中提交真实数据库密码**，使用环境变量或配置文件
4. **三平台的 CSS 选择器都可能随网站改版而失效**，这是正常的维护成本

---

## 9. 上手学习路径（7天计划）

### 第 1 天：环境搭建 + 跑通项目
- [ ] 安装 Python 3.7+、Chrome、ChromeDriver、MySQL
- [ ] `pip install` 所有依赖
- [ ] 启动 MySQL，确认服务正常运行
- [ ] 运行 `Product_Analysis_V1.0.py`（最简版，减少干扰）
- [ ] 成功看到数据采集和图表输出

### 第 2 天：理解核心代码（爬虫部分）
- [ ] 精读 `init_driver()` — 理解 Selenium WebDriver 初始化
- [ ] 精读 `get_taobao_data()` — 理解「加载页面→等待登录→滚动→解析DOM→清洗数据」全流程
- [ ] 对比 `get_jd_data()` 和 `get_pinduoduo_data()` 的差异
- [ ] 理解 CSS 选择器的作用（类名查找 HTML 元素）

### 第 3 天：理解数据处理和输出
- [ ] 精读 `run()` — 理解整体编排逻辑
- [ ] 精读 `visualize_data()` — 理解 matplotlib 子图布局
- [ ] 精读 `save_to_mysql()` — 理解 pymysql 建库建表批量插入
- [ ] 尝试修改图表颜色、标题

### 第 4 天：对比版本差异 + 动手修改
- [ ] 对比 V1.0 → V1.1 → V1.2 → V1.3 的 diff（重点看 `__main__` 和 `run()`）
- [ ] 试着修改 keyword 为其他商品名（如 "iphone15"），观察结果差异
- [ ] 试着增加 `max_items` 到 20，看能否爬到更多数据

### 第 5 天：动手练习
- [ ] 练习 1：修改 `visualize_data()` 增加一个新的图表类型（如饼图）
- [ ] 练习 2：给数据库表 `products` 增加一个新字段（如 `product_name`），修改对应代码
- [ ] 练习 3：给 `ECommerceScraper` 类增加日志功能（用 `logging` 替代 `print`）

### 第 6 天：理解反爬与健壮性
- [ ] 研究三个平台的反爬策略（验证码、IP限制、请求频率）
- [ ] 学习 Selenium 的反反爬技巧（随机等待、UA伪装、代理IP）
- [ ] 尝试给爬虫增加异常重试机制

### 第 7 天：综合实战
- [ ] 自选一个电商平台（如苏宁、唯品会），仿照现有代码实现数据采集
- [ ] 完整跑通「采集→分析→可视化→存储→导出 CSV」全流程
- [ ] 代码 review：对比自己和原始代码的差异

---

## 10. 避坑指南

### 历史遗留问题

| 问题 | 影响 | 状态 |
|------|------|------|
| **V1.3 第 1 行 `import keyword` 是错误导入** | Python 内置 `keyword` 模块被意外导入，虽然不影响运行（方法中的 `keyword` 是参数名而非模块调用）但造成混淆 | ❌ 未修复 |
| **拼多多的 `get_pinduoduo_data()` 未使用 `self.init_driver()`** | 与其他两个平台代码风格不一致，driver 管理方式不同 | ❌ 未修复 |
| **4 个版本文件重复率 > 95%** | 修改一处功能需要改 4 个地方 | ❌ 未重构 |
| **数据库密码硬编码** | 默认密码 `123456` 暴露在代码中 | ❌ 未修复 |
| **异常处理过于宽泛** | `except Exception` 吞掉了所有错误，难以排查问题 | ❌ 设计如此（教学项目） |

### 常见踩坑点

| 坑 | 现象 | 避坑方法 |
|----|------|---------|
| **ChromeDriver 版本不匹配** | `This version of ChromeDriver only supports...` | 严格对齐 Chrome 和 ChromeDriver 版本号 |
| **淘宝/京东页面结构变化** | CSS 选择器找不到元素，返回空数据 | 用浏览器 F12 检查当前页面 DOM，更新选择器 |
| **拼多多反爬严格** | 经常超时或返回空列表 | 增大 `time.sleep()`，降低并发频率 |
| **MySQL 连接被拒** | `Access denied for user 'root'@'localhost'` | 确认 MySQL 密码，或用 `mysql -u root -p` 先验证 |
| **matplotlib 图表不显示** | 运行后无窗口弹出 | 检查是否在无 GUI 环境（如 WSL/SSH），改用 `plt.savefig()` 仅保存文件 |
| **扫码超时** | 60 秒内未完成登录，该平台数据为空 | 提前打开对应平台网页确认已登录，再运行脚本 |
| **`filter(str.isdigit, ...)` 导致销量为 0** | 页面文案变化（如新增符号）导致数字提取失败 | 检查实际 HTML 元素文本，调整清洗逻辑 |

### 容易出 Bug 的模块

| 模块 | 风险等级 | 原因 |
|------|---------|------|
| `get_pinduoduo_data()` | 🔴 高 | 反爬最严、CSS 选择器最深（多层嵌套）、driver 管理独立 |
| `get_taobao_data()` | 🟡 中 | 需要扫码登录、CSS 类名可能是动态生成的 |
| `get_jd_data()` | 🟡 中 | 价格和销量的 DOM 嵌套查找 (`find().find()`) 易出现 NoneType 错误 |
| `visualize_data()` | 🟢 低 | 逻辑简单，但 `ylabel` 写成了 `avgp_rice`（typo） |

---

> **本指南基于项目文件实际内容生成，标注「待补充」的项表示当前代码/文档中未找到相关信息。**
>
> 最后更新：2026-06-16
