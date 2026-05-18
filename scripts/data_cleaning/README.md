# 河北高考 Excel 数据清洗

## 运行方式

在项目根目录运行：

```powershell
& 'C:\Users\liuli\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts\data_cleaning\clean_excel.py --input . --output data\cleaned
```

如果使用系统 Python，需要先安装：

```powershell
pip install openpyxl
```

## 输入文件识别

脚本会自动识别当前目录下的 `.xlsx` 文件：

- `*高考成绩统计表.xlsx`：作为一分一档/位次表来源。
- `*本科批平行志愿投档统计表.xlsx`：作为本科批投档数据来源。
- `*第一志愿录取后统计表.xlsx`：当前不参与推荐位次计算，自动忽略并写入报告。
- `~$*.xlsx`：Excel 临时锁文件，自动忽略。

## 输出目录

默认输出到 `data/cleaned/`：

- `rank_table/rank_2023.json`
- `rank_table/rank_2024.json`
- `rank_table/rank_2025.json`
- `rank_table/all_rank.json`
- `admission/admission_2023.json`
- `admission/admission_2024.json`
- `admission/admission_2025.json`
- `admission/all_admission.json`
- `reports/data_cleaning_report.md`
- `reports/data_cleaning_report.json`

同时生成 CSV，方便用 Excel 或人工抽查。

## 关键字段

### rank_table

- `year`：年份。
- `subject`：`physics` 或 `history`。
- `score`：分数档。
- `count_at_score`：该分数人数。
- `cumulative_rank`：累计人数，也就是该分数对应位次。
- `source_file` / `source_row`：来源文件和行号。

### admission

- `year`：年份。
- `subject`：当前投档表科目组合，目前现有本科批投档表均解析为 `physics`。
- `school_code`：院校代号。
- `school_name`：去掉 `[公办]` 等标签后的院校名称。
- `school_name_raw`：原始院校名称。
- `school_tags`：如 `公办`、`民办`、`独立学院`。
- `major_code`：专业代号。
- `major_name`：专业名称。
- `min_score`：投档最低分。
- `min_rank`：按同年同科目一分一档表补齐的位次。
- `volunteer_no`：投档最低分同分考生排序项中的志愿号，不是招生计划数。
- `source_file` / `source_row`：来源文件和行号。

## 已验证样例

2025 年物理组，北京林业大学人工智能：

- 投档最低分：`628`
- 对应位次：`10271`
- 来源行：`2025年本科批平行志愿投档统计表.xlsx` 第 `848` 行

