# csvkit-lite 🗂️

A tiny, zero-dependency, single-file CSV toolkit. `csvkit` is great — but heavy to install and overkill when you just want to peek at a CSV, convert it to JSON, or merge a few files. csvkit-lite does the 5 most common jobs with **zero dependencies** (stdlib only) in **one file**.

轻量级 CSV 工具箱：csvkit 功能强大但依赖重、装得慢。csvkit-lite 只做最常用的 5 件事——**纯标准库、零依赖、单文件**。

## Install

```bash
pip install csvkit-lite
# or just download csvkit_lite.py — it's a single file, no install needed
# 或者直接下载 csvkit_lite.py 单文件，无需安装
```

## Usage

```bash
# Pretty-print as an aligned table (CJK-aware)
# 表格化预览（中文对齐）
csvkit-lite view data.csv
csvkit-lite view data.csv --head 50
csvkit-lite view data.csv --tail 10

# Convert to JSON (array of objects, or --arrays for array of arrays)
# 转 JSON（默认对象数组，--arrays 输出数组的数组）
csvkit-lite tojson data.csv -o data.json
csvkit-lite tojson data.csv --arrays

# Merge multiple CSVs, aligning columns (missing cells become empty)
# 合并多个 CSV（列自动对齐，缺列补空）
csvkit-lite merge a.csv b.csv -o all.csv

# Filter rows: >/>=/</<=/==/!= supported
# 按条件筛选
csvkit-lite filter data.csv --where "age>30"
csvkit-lite filter data.csv --where "city==上海" -o shanghai.csv

# Column stats: row count, non-empty counts, min/max/avg for numeric columns
# 列统计：行数、非空数、数值列的 min/max/avg
csvkit-lite stats data.csv
```

## Smart defaults

- **Encoding auto-detect**: utf-8 (with BOM) → gbk
- **Delimiter auto-detect**: comma / semicolon / tab / pipe
- **编码自动识别**：utf-8（含 BOM）→ gbk
- **分隔符自动探测**：逗号 / 分号 / tab / 竖线

## Example

```
$ csvkit-lite view data.csv
姓名 | 年龄 | 城市 | 工资
-----+------+------+------
张三 | 28   | 北京 | 15000
李四 | 35   | 上海 | 22000

$ csvkit-lite stats data.csv
rows: 5
columns: 4

  姓名: non-empty 5/5
  年龄: non-empty 5/5 | min 25 | max 42 | avg 32.20
  城市: non-empty 4/5
  工资: non-empty 5/5 | min 9000 | max 22000 | avg 15200.00

$ csvkit-lite filter data.csv --where "年龄>30"
姓名,年龄,城市,工资
李四,35,上海,22000
王五,42,广州,18000
```

## vs csvkit

| | csvkit-lite | csvkit |
|---|---|---|
| Dependencies | 0 (stdlib only) | 10+ |
| Install size | 1 file (~10KB) | ~MBs |
| Covers | view/tojson/merge/filter/stats | everything incl. SQL |

Need SQL joins and 20 subcommands? Use csvkit. Just want the daily 5? Use csvkit-lite.

## License

MIT
