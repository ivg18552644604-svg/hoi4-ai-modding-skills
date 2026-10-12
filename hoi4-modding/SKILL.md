---
name: hoi4-modding
description: 编写、修改与调试钢铁雄心4（Hearts of Iron IV / HOI4 / 钢4 / P 社模组）模组代码。当用户要求创建或修改 HOI4 模组、写/改国策树（national focus / focus tree）、事件（events）、决议（decisions）、国家精神（national spirit / ideas）、军工组织（MIO / military_industrial_organization / 军工集团）、内政工业公司或集团（industrial_concern / 国家工业公司）、科技（technologies）、省份与州（states / provinces）、国家历史（history）、角色（characters）、本地化（localisation / loc）、scripted effects / triggers、descriptor.mod / .mod 文件、给别的模组做子模组（sub-mod / 兼容式扩展 / 前置依赖），或遇到模组报错（error.log、焦点不显示、事件不触发、localisation 显示 key 原文）时，务必使用本技能——即使对方没提"模组"二字（例如"帮我的德国国策树加个分支""给这个 tag 加个事件""给三军设计做个兼容子模组"）。以最新版本 1.19（Operation Postern）语法为准（含 1.19 modifier 改名），提供完整工作流：模组结构、子模组兼容、编码规范、各系统写作要点、调试方法、可复用自检脚本与交付前自检清单；内置八大主题游戏机制知识参考（政治/工业/科研/军事/外交/领土/人物/情报），保证数值与机制设计合理（来源：hagane.works 钢之工坊知识社区，1.19.2 核对/实测）。
---

# HOI4 模组代码技能

你是在写钢铁雄心 4（Hearts of Iron IV）的模组代码——Paradox Script Language（PSL）。**目标版本以 1.19.2（Operation Postern）为准**，同时写法与 1.14–1.18 基本兼容（差异点已在参考文档标注）。

本技能提供：工作流、编码规范、各系统的写作要点、调试方法、**可复用自检脚本**和交付前自检清单；**详细的语法速查（各系统全部字段、坑、版本差异）在 `references/hoi4-syntax-reference.md`，动笔前先读对应章节**（参考文档较长，包含目录，按需跳读）。

## 工作流

1. **理解需求**：目标国家/tag、内容范围（国策/事件/决议/科技/军工组织 MIO/内政工业公司 industrial_concern/地图/历史…）、目标游戏版本、是新建还是修改现有模组、**是否为给别的模组做的子模组（前置依赖是哪个、要不要避免覆盖）**、是否涉及 `replace_path` 覆盖原版目录、输出文件写到哪（当前工作区或用户指定路径）。信息不足先问。**涉及机制数值的设计（外交/自治/科研/人物/军事/工业等）先读 `references/gameplay-politics-economy-research.md` 或 `references/gameplay-military-diplomacy-territory-people.md` 对应章节再动笔**——数值与作用域要符合游戏机制，不只是语法正确。
2. **规划结构**：先铺目录树（见下），再逐文件写，让用户一眼看到整体。**做子模组时先决定"新增哪些文件、是否与主机模组同名"**——优先全新增、零覆盖（见 references §11.1）。
3. **代码与本地化同步写**：每个 id（国策/事件/决议/精神/科技/角色）先定 key，写完代码立刻补 loc，避免"写完全部代码再补 loc 漏掉一半"。
4. **验证**：交付前运行技能自带的验证脚本 `python scripts/validate_hoi4_mod.py <模组目录>`（检查括号/引用闭环/事件 namespace/整数 id/loc 覆盖/BOM 规范）；**若模组含 MIO 或引用了其它模组的装备/装备组/科技类别，再跑 `python scripts/check_mio_references.py <模组目录> [被引用的模组目录…]`** 交叉核验 `equipment_type` / `research_categories` 的 token 是否真实存在。最后按「自检清单」复核。**先跑脚本再人工复核**，不要反过来。
5. **交付时给出**：目录结构说明 + 安装/加载方式（放进 `文档/Paradox Interactive/Hearts of Iron IV/mod/`）+ 调试提示（reload 命令，见下）+ 若有子模组依赖，说明**加载顺序（前置模组要排在本模组前面）**。

## 验证策略（防止过度核查，也防止漏查）

优先级从高到低，**能满足就不要再往下走**：

1. 先跑 `scripts/validate_hoi4_mod.py`——它覆盖大部分可客观判定的检查。**模组含 MIO 或引用了别的模组的装备/科技类别时，再跑 `scripts/check_mio_references.py`**（`equipment_type` / `research_categories` 的 token 是否存在，含 `--ref` 传入主机模组）。
2. 只对脚本覆盖不到的细节做人工核对：效果/触发器名是否真实存在、modifier 名是否 1.19 标准写法、目标版本的特殊差异。
3. 需要核实时，**按关键词定位**，不要全量扫描：本机如有游戏安装，用它的 `documentation/effects_documentation.md`、`triggers_documentation.md`、`modifiers_documentation.md` 和原版 `common/` 文件做对照（常见安装位置如 `D:/SteamLibrary/steamapps/common/Hearts of Iron IV`，不确定就问用户）；没有本机游戏就用 Paradox Wiki。
4. 引用不确定的原版资源（idea id、GFX 名、州 ID）时：能查到证据就用证据，查不到就**在交付说明中明确标注"待玩家核实项"**，不要假装确定。

这样做的意义：全量交叉验证一次可能要几十分钟（实测有 84 分钟的案例），而绝大多数检查是脚本 1 秒能完成的；把模型的时间花在"判断设计是否合理"上，而不是机械核对。

## 编码规范（为什么这些很重要）

- **文件编码**：`.txt`/`.mod` 用 UTF-8 **无 BOM**；localisation `.yml` 必须 UTF-8 **带 BOM**。BOM 缺失会让整份 loc 文件不加载（表现为游戏里全是裸 key）。
- **BOM 后处理（易漏）**：用文本写入工具（如 Write）生成的 `.yml` **默认不带 BOM**，写完必须补一个 `\xef\xbb\xbf` 前缀；`.txt`/`.mod` 则要确认**没有** BOM。交付前抽查：`head -c 3 文件 | od -An -tx1` —— yml 应为 `ef bb bf`，txt/mod 不应是。
- **玩家可见文本一律走 localisation**，PSL 正文里不放裸中文/裸英文长句。理由：loc key 不一致是模组 bug 的最大来源，且只在 error.log 和游戏内显示 key 原文时暴露。
- **命名**：焦点/决议 id 用大写下划线国家前缀（`FRA_RECOVERY`）+ loc；事件 id 必须 `add_namespace = xxx` 且 id 为 `xxx.整数`（非整数 id 会被当成同一事件）；脚本 effect/trigger 名小写下划线。
- **引用闭环**：`prerequisites`（**复数**）、`add_ideas`、`country_event`、`add_technology` 等引用的 id 必须真实存在（你的模组或原版）。缺引用的国策会永远置灰、精神不生效，error.log 里往往也只是个 warning，不仔细看发现不了。
- **语法**：`key = value`；块用 `{ }`；含空格/特殊字符的值加引号；效果名写全（`add_political_power = 150`，不是 `political_power`）；**触发器与 modifier 对大小写敏感**（不要模仿原版遗留的 `army_org_Factor` 这类笔误）。
- **1.19 modifier 名**：旧的 `stability`→`stability_factor`、`war_support`→`war_support_factor`、`factory_output`→`industrial_capacity_factory`；`political_power_gain`、`consumer_goods_factor`、`research_speed_factor`、`recruitable_population_factor`、`local_manpower`、`<意识形态>_drift` 等不变。效果名（`add_stability` 等）不受影响。完整表见 references §4。
- **版本**：`descriptor.mod` 里写 `supported_version = "1.19.*"`（玩家版本为 1.19.2.0.3eb1 时可精确到 `"1.19.*"` 通配即可）。若用户明确要旧版本，按旧版本写法并注明差异。
- **环境限制**：如果当前会话是纯文本模型（无视觉能力），**不要生成或读取任何图片**（thumbnail、国旗、角色立绘），在交付说明中用"占位，玩家可自行替换"注明即可；也不要调用图像工具。

## 模组结构模板

```
my_mod/
├── descriptor.mod            # 必须叫这个名；UTF-8 无 BOM
├── thumbnail.png             # 可选，<1MB
├── common/
│   ├── national_focus/       # 国策树 *.txt
│   ├── events/               # 事件 *.txt（注意：原版在 events/，不是 common/events/）
│   ├── decisions/            # 决议 *.txt
│   ├── decisions/categories/ # 决议类别 *.txt（1.19 惯例：类别与决议分两个目录）
│   ├── ideas/                # 国家精神 + 内政工业公司（industrial_concern）
│   ├── idea_tags/            # 理念槽位注册（新增自定义类别时才需要）
│   ├── military_industrial_organization/organizations/   # 军工组织 MIO（需 AAT DLC）
│   ├── equipment_groups/     # MIO 装备组 mio_cat_*（如需自定义分组）
│   ├── technologies/         # 科技；新分支还要改 interface/countrytechtreeview.gui
│   ├── scripted_effects/  scripted_triggers/  scripted_localisation/
│   ├── characters/           # 角色：将领/政治家/设计师/特工
│   └── country_tags/  countries/      # 仅新增国家时需要
├── history/
│   ├── countries/            # <TAG>_<名字>.txt，首 3 字母必须是 TAG
│   ├── states/               # 州历史；id 必须从 1 连续到最大值
│   └── units/                # OOB，用 load_oob 引用
└── localisation/
    ├── english/xxx_l_english.yml        # 语言代号必须拼对（l_simp_chinese 而非 l_chinese）
    └── simp_chinese/xxx_l_simp_chinese.yml
```

`descriptor.mod` 最小模板：

```
name="My Mod"
supported_version="1.19.*"
tags={ "Alternative History" }
path="mod/my_mod"
```

提示用户：本地 mod 路径**不能含非 ASCII 字符**（中文路径加载不了）；整目录替换原版用 `replace_path="history/countries"` 这类声明。

**本地 mod 的注册文件（易错）**：在 `mod/` 目录下还必须有**与模组文件夹同名的 `.mod` 文件**（如 `mod/my_mod.mod`），里面写 `path=".../mod/my_mod"` 指向文件夹；文件夹内的 `descriptor.mod` 负责元数据（name/version/tags/supported_version/dependencies）。两者内容可基本一致，但**根目录 `.mod` 的 `path` 是加载器定位文件夹的依据**。

**子模组（给别的模组做兼容扩展）**：给 `mod/` 下放两个文件即可——文件夹内的 `descriptor.mod` 与根目录的同名 `.mod`；用 `dependencies={ "前置模组显示名" }` 声明前置。策略上**优先零覆盖**（全新增文件、不写 `replace_path`、不用主机模组已有的文件名），并让玩家把前置模组排在本模组**前面**加载。细节见 `references/hoi4-syntax-reference.md` §11.1。

## 核心系统写作要点

### 国策树（common/national_focus/*.txt）
- 顶级块 `focus_tree = { id = ... }`，`focus = { }` 必须嵌在树内。
- 新树要给目标 tag 高分才会被采用：`country = { factor = 0 modifier = { add = 20 tag = FRA } }`（**评分块 modifier 内用 `tag`，不是 `original_tag`**；`original_tag` 用于 `allowed` 等触发器位置，表示"原始标签"）。全游戏只能有一棵 `default = yes` 树。
- 国策字段：`id / icon / x / y / cost / prerequisites = { focus = A } （复数键！）/ mutually_exclusive = { focus = B } / completion_reward = { } / available = { } / ai_will_do = { }`。
- 布局：水平一格约 96px、垂直一行约 130px；互斥的两条线放不同 y 行，避免图标重叠。
- 只触发一次的分支用 `cancel_if_not_valid = yes`；跳过式前置用 `available_if_capable = yes` 或 `bypass`；另有 `available_if_capitulated = no`、`search_filters = { FOCUS_FILTER_INDUSTRY }` 等可用。
- 焦点 ID 本身即本地化 key，记得写 `<ID>_desc`。
- 想保留原版树并往里加焦点：用另一棵树的 `focus_tree` 里 `shared_focus = 原版焦点ID` 引入再扩展，**不要**为同一 tag 写两棵评分树（会整体替换）。涉及外交（阵营/宣战理由/好感方向）、自治档、人物特质、军事数值、州转移等深度设计，先读 gameplay 知识文件对应章节。

### 事件（events/*.txt）
- **先 `add_namespace = xxx`（必须在事件块外、文件顶部），再写事件**；`id = xxx.1`（整数）。缺失时事件不生效/报 malformed token。
- 只由脚本触发的剧情事件必须写 `is_triggered_only = yes`；一旦混入 `mean_time_to_happen` 就会随机触发（"事件莫名弹出"的头号原因）。两个都写时触发器先满足也会被 MTTH 抢跑。
- `hidden = yes` 做无弹窗环节；剧情链用 `hidden_effect` + 延迟 `country_event = { id = xxx.2 days = 1 }`。
- 多候选事件用 `weight = { base = 100 modifier = { ... } }`；单事件不同分支用 option 内 `trigger = { }`。
- title/desc/option name 全是 loc key（`xxx.1.t / xxx.1.d / xxx.1.a`），命名在 1.19 原版一致。

### 决议（common/decisions/*.txt + categories/）
- 类别定义在 `common/decisions/categories/`，决议本体在 `common/decisions/`（1.19 惯例拆两个目录，但都放 decisions 文件内的 `类别id = { 决议id = {...} }` 块中也仍可加载）。
- 决议块**没有 `name =` 字段**：显示名 loc key = 决议 id 本身（+ `_desc`），类别同理（key = 类别 id）。别写 `category_decision_name` 旧式 key。
- 三个判断块语义不同：`allowed`（开局/读档查一次，放国家级固定条件，如 `original_tag = SAF`）、`visible`（逐帧，控制显示）、`available`（逐帧，控制可点）。**别把动态条件放 allowed**。
- `complete_effect`（完成时）、`remove_effect`（手动移除，可返还 PP）、`cancel_effect`（被取消时），三者勿混。
- `ai_will_do = { factor = 10 modifier = { ... } }` 控制 AI 倾向；`days_remove`（完成后从列表消失延迟）、`days_re_enable`（可重复决策冷却）、`fire_only_once`、`priority`、`target_trigger`（目标型决策）都是常见字段。

### 国家精神（common/ideas/*.txt）
```
ideas = {
    fra_spirits = {                    # 分组层（原版风格，合法；分组名不是 id）
        fra_recovery = {
            name = fra_recovery        # loc key
            modifiers = {
                stability_factor = 0.10        # 1.19 写法（旧 stability 已改名）
                consumer_goods_factor = -0.05
            }
        }
    }
}
```
- `name` 是 loc key；精神 id 就是 `add_ideas` 引用的那个 id（**第二层缩进的那个**），拼写必须完全一致。
- 一次性精神用 `cancel_if_not_valid = yes`；限时精神用 `add_timed_idea = { idea = X days = 365 }`（焦点/事件里调用）。
- 1.19 常用 modifier 对照（**旧名 → 1.19 名**）：`stability → stability_factor`、`war_support → war_support_factor`、`factory_output → industrial_capacity_factory`（另 `industrial_capacity_dockyard`、`industrial_capacity_factory_powered`）。不变：`political_power_gain`、`consumer_goods_factor`、`research_speed_factor`、`production_factory_efficiency_gain_factor`、`recruitable_population_factor`、`local_manpower`、`democratic_drift`/`fascism_drift`/`communism_drift` 等。

### 军工组织（MIO）与内政工业公司（industrial_concern）

**两个不同系统，别搞混**（完整字段与先例见 references §5）：

- **MIO（军工组织）** `common/military_industrial_organization/organizations/*.txt`：顶层块键即 MIO token；需 DLC「Arms Against Tyranny」（写 `allowed = { has_dlc = "Arms Against Tyranny" }`）。核心字段 `name`(loc key) / `icon`(GFX) / `allowed`（开局固定门槛）/ `available = { owner = { ... } }`（逐帧、国家作用域）/ `ai_will_do` / `equipment_type`（装备原型 token 或 `mio_cat_*` 装备组，**组可嵌套**）/ `research_categories`（`common/technology_tags/*.txt` 的**裸列表 token**）/ `initial_trait`（可带 `token`）/ `trait`（升级节点，含 `position`/`any_parent`/`equipment_bonus`/`organization_modifier`/`production_bonus`）。**玩家专属 MIO 的标准写法：`available = { owner = { is_ai = no } }` + `ai_will_do = { base = 0 }`**；扩展原版通用组织用 `override_trait`/`add_trait`（同 token 覆盖），别重写整块。
- **内政工业公司/集团（`industrial_concern` 理念）** 写在 `common/ideas/*.txt`，**顶层键固定 `industrial_concern`**（该槽位在 `common/idea_tags/00_idea.txt` 注册；同槽位**同时只能启用一个公司**），显示在内政页「研究与生产」区块，用政治点购买：`cost = 150`、`removal_cost = 0`（**150 的默认值来自 idea_tags 里 `research_production` ledger 组的 `cost`，单条 idea 不写也按组默认**）、`picture = generic_industrial_concern_1/2/3`、`traits = { industrial_concern }`、`research_bonus`、`modifier`。**"仅玩家可用"：`available = { is_ai = no }` + `ai_will_do = { factor = 0 }`**（原版 MIO 无此先例，`owner = { is_ai = no }` 模式来自成熟工坊 mod 实践，`is_ai` 为文档收录触发器）。按公司名给差异化加成（民工 → 建造/生活消费品/基建/资源；军工 → `industrial_capacity_factory`/`industrial_capacity_dockyard`/产能效率/建造速度/MIO 运营）。loc 要补 `name` 与 `<name>_desc`。
- **图标（两者通用）**：MIO `icon` 填**完整 GFX 精灵名**；idea `picture` **只填后半段**（引擎自动拼 `GFX_idea_<picture>`）。贴图 **64×64 PNG**（不必转 DDS）放 `gfx/interface/ideas/`，在 `interface/*.gfx` 里定义 `spriteType`（`texturefile` 指到 png）；无图就复用原版 `GFX_idea_generic_industrial_concern_1/2/3`。AI 生图注意裁水印再缩 64²。MIO 升级树标题 `tree_header_text = { text = <loc key> x = N }` 可重复多个。

### 科技 / 州省 / 国家 / 角色
- 科技（`common/technologies/`）：**前置写在「前置科技」的 `path = { leads_to_tech = ... }` 里**——科技块内写 `prerequisites` 会报 `Unknown modifier` 且整块被忽略；folder 的 position 坐标 **y=横轴（年份方向）、x=纵轴（换行）**，填反不报错但节点落进别人链条。新科技若不在现有 path 上、又没自建页签 GUI，游戏里不会显示（自建页签五件套见 gameplay 文件一 §3.4）。
- 州（`history/states/`）：`state = { id = N ... }`，**id 必须从 1 连续到最大值**——删州必须重排 ID，否则无 debug 加载直接崩溃。**新国家不要凭空造州 ID**：先在本机 `history/states/` 找真实州（如云南 = `325-Yunnan.txt`，昆明省 1319），或使用"原版最大州 ID + 1"并标注玩家需核实。可用 `localisation/english/state_names_l_english.yml` 的 `STATE_N` 条目与 states 文件名互证省州 ID。资源和建筑写法是"产量"语义（`resources = { tungsten = 5 }`）。
- 国家（`history/countries/`）：文件名首 3 字母 = TAG；`capital` 引用的省份 ID 必须真实存在；新 tag 必须在 `common/country_tags/` 注册且全局唯一。
- 角色（`common/characters/`）：`characters = { 名字 = { name = loc_key country = TAG role = ... } }`；角色系统是 1.13+ 的标准做法，别再用旧式 `country_leader` 文件。

### 本地化（localisation/）
- 格式：`key:0 "文本"`，行首不缩进；同 key 后加载的覆盖先加载的；数字支持最多 3 位小数。
- 先写 `_l_english` 打底（缺语言时回退英文），再写 `_l_simp_chinese`。引用别的 key 用 `$key$`；可含 `[FROM.GetName]` 这类作用域引用。**覆盖原版键要放 `localisation/<语言>/replace/` 目录**（放普通目录也生效但 error.log 记 loc key collisions）。
- 命名惯例：国策/决议加 `_desc`；事件 `namespace.id.t/.d/.a`；精神/角色按 `name` 字段的 key 补条目。

### Scripted effects / triggers
- `common/scripted_effects/*.txt`：`my_effect = { 效果 }`，调用 `my_effect = yes`。多处复用的逻辑（如一条事件链的公共结算）抽成 scripted effect，大幅减少重复代码和引用不一致的 bug。
- `common/scripted_triggers/*.txt`：`my_trigger = { 条件 }`，调用 `my_trigger = yes`（别大写）。
- 1.19 新增：`common/script_math_functions` 支持 `pow/sqrt/cos/sin/tan/exp/log` 等数学函数；`impassable_ignored_links` 用于配置不透明州联通的忽略项。
- 资源效果统一用单数 `add_resource = { type = steel amount = 5 state = 42 days = 60 show_state_in_tooltip = no }`（1.19 已无 `add_resources`）。
- 阵营效果：`create_faction = X` 仍可用但已标记 deprecated，新推荐 `create_faction_from_template`（配合 Deeper Factions 模板机制）；简单场景两者都能用，教学优先提后者、兼容用前者。

## 调试指引（交付时告诉用户）

- **日志**：`文档/Paradox Interactive/Hearts of Iron IV/logs/error.log`，每行带文件和行号，崩溃/加载问题先看它。
- **控制台热重载**（游戏内按 `~`）：`reload focus`、`reload events`、`reload decisions`、`reload localisation`、`tdebug`（显示 tooltip id）。改代码不用重启游戏。
- 常见报错 → 原因速查（完整表格见 reference 第 12 节）：
  - `[focus] unexpected token` → 括号错位/未闭合，或 `focus` 块写到了 `focus_tree` 外
  - `[event] malformed token` → `add_namespace` 缺失或事件 id 非整数
  - 游戏内显示裸 key → localisation 缺条目、key 拼写不一致、loc 文件 BOM/文件名错
  - 焦点永远置灰 → `prerequisites` 引用了不存在的焦点，或误写单数 `prerequisite`
  - 点击完成但无效果 → 效果名拼写错误（如 `political_power` 而非 `add_political_power`），或 modifier 用了 1.19 已改名的旧写法（`stability` → `stability_factor`），均静默无效
  - MIO 组织不出现/永不可用 → 把动态条件写进了 `allowed`、缺 DLC 门槛、或 `equipment_type` 引用了不存在的装备/装备组 token
  - 内政页看不到工业集团 → 顶层键不是 `industrial_concern`、漏 `traits = { industrial_concern }`、或 `cost`/loc key 不对

## 交付前自检清单（先跑脚本，再逐项复核）

- [x] 运行 `python scripts/validate_hoi4_mod.py <模组目录>`：括号配对、国策引用闭环、互斥双向、事件 namespace/整数 id、idea 引用闭环、loc 覆盖、BOM 规范全部通过
- [x] 若含 MIO：运行 `python scripts/check_mio_references.py <模组目录> --ref <主机模组目录> --game <游戏目录>`，`equipment_type` / `research_categories` 引用全部存在
- [ ] 每个被引用的 id（焦点/事件/决议/精神/科技/角色/州）都已定义且拼写一致
- [ ] 事件文件有 `add_namespace`，所有事件 `id = namespace.整数`
- [ ] 只想脚本触发的事件都写了 `is_triggered_only = yes`，且没有混入 `mean_time_to_happen`
- [ ] 每个国策/事件/决议/精神都有英文 + 简体中文 loc 条目；决议/类别显示名 key = 其 id 本身
- [ ] loc 文件名是 `*_l_english.yml` / `*_l_simp_chinese.yml`，内容 `key:0 "..."`、行首无缩进、UTF-8 带 BOM
- [ ] 效果名全部正确（`add_political_power`、`add_stability`、`add_resource`…）；modifier 名用 1.19 标准（`stability_factor` 等，见 references §4）
- [ ] 国策树 `country` 评分块用 `tag = 目标TAG`；全模组只有一棵 `default = yes` 树
- [ ] 新国家州/省 ID 经本机核实（不凭空占位）；state id 连续无缺号；`capital`/`province` 引用真实存在（注意拼写 `province`）
- [ ] 科技前置写在 `path`（非 `prerequisites`）；folder 坐标未填反；涉及外交/人物/军事/工业数值时已对照 gameplay 知识文件
- [ ] descriptor 存在、`supported_version` 与目标版本匹配、路径不含非 ASCII 字符
- [ ] **若含 MIO**：`allowed` 内只放开局固定门槛（DLC/国家），玩家专属用 `available = { owner = { is_ai = no } }` + `ai_will_do = { base = 0 }`；`equipment_type` / `research_categories` 的每个 token 都真实存在（含主机模组扩展，用 `check_mio_references.py` 核验）
- [ ] **若含内政工业公司（industrial_concern）**：顶层键为 `industrial_concern`，`cost` / `traits` / `modifier` / `available` 齐备，`name` 与 `<name>_desc` loc 齐全，"仅玩家"用 `is_ai = no` + `ai_will_do = { factor = 0 }`
- [ ] **若为子模组**：`dependencies` 声明了前置模组、采用零覆盖（不与主机模组同名的数据文件）、自定义 token 前缀已做撞名扫描（本模组/主机模组/原版/其余本地 mod）
- [ ] 生成的 `.yml` 已补 BOM、`.txt`/`.mod` 确认无 BOM（`head -c 3 文件 | od -An -tx1` 抽查）
- [ ] 纯文本环境：确认没有生成/读取图片文件，图片资源以占位说明处理

## 完整最小示例（国策 → 触发事件，1.19 写法）

```
# common/national_focus/nanzhao_focus.txt
focus_tree = {
    id = nanzhao_tree
    country = { factor = 0 modifier = { add = 20 tag = NAN } }   # 评分块用 tag
    default_focus = { id = NAN_DEVELOPMENT }
    focus = {
        id = NAN_DEVELOPMENT
        icon = GFX_focus_nanzhao_dev
        x = 0
        y = 0
        cost = 10
        completion_reward = {
            add_political_power = 100
            country_event = { id = nanzhao.1 days = 1 }
        }
    }
}

# events/nanzhao_events.txt
add_namespace = nanzhao                              # 事件块外，文件顶部
country_event = {
    id = nanzhao.1
    title = nanzhao.1.t
    desc = nanzhao.1.d
    is_triggered_only = yes
    option = {
        name = nanzhao.1.a
        add_stability = 0.05
    }
}

# localisation/english/nanzhao_l_english.yml
l_english:
 NAN_DEVELOPMENT:0 "Consolidate Nanzhao"
 NAN_DEVELOPMENT_desc:0 "Unify the southern tribes."
 nanzhao.1.t:0 "A New Era"
 nanzhao.1.d:0 "The southern banner rises."
 nanzhao.1.a:0 "Long live Nanzhao!"
```

写完代码若不确定某个 effect/trigger/modifier 是否存在或拼写，先查本机游戏的 `documentation/`（effects/triggers/modifiers 三个文档），再查 wiki；确认不了就按「验证策略」第 4 条标注待核实。
